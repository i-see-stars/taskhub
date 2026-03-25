"""Issue tracking application services.

Orchestrates domain objects, repositories, and event publishing.
No HTTP or database framework knowledge — only domain and repository abstractions.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.issue_tracking.domain.entities import Comment, Issue, Project
from app.issue_tracking.domain.exceptions import (
    AssigneeNotProjectMember,
    InsufficientPermissions,
    IssueNotFound,
)
from app.issue_tracking.domain.value_objects import (
    IssueStatus,
    IssueType,
    Priority,
    ProjectRole,
)
from app.issue_tracking.infrastructure.models import (
    CommentModel,
)
from app.issue_tracking.infrastructure.repositories import (
    PostgresIssueRepository,
    PostgresProjectRepository,
)
from app.shared.domain.identifiers import (
    CommentId,
    IssueId,
    ProjectId,
    UserId,
)

logger = logging.getLogger(__name__)


class ProjectAppService:
    """Application service for project management.

    Handles project CRUD and membership operations.
    Delegates persistence to PostgresProjectRepository.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        self._session = session
        self._repo = PostgresProjectRepository(session)

    async def create_project(
        self,
        owner_id: str,
        name: str,
        key: str,
        description: str | None,
    ) -> Project:
        """Create a new project and set creator as owner.

        Args:
            owner_id: The creating user's ID.
            name: Project display name.
            key: Unique project key (e.g. 'TASKHUB').
            description: Optional description.

        Returns:
            Created Project aggregate.
        """
        project = Project(
            project_id=ProjectId(""),  # assigned on flush
            name=name,
            key=key,
            description=description,
        )
        project.add_member(UserId(owner_id), ProjectRole.OWNER)
        saved = await self._repo.save(project)
        await self._session.commit()
        return saved

    async def add_member(
        self,
        project_id: str,
        requesting_user_id: str,
        target_user_id: str,
        role: ProjectRole,
    ) -> None:
        """Add a member to a project. Requester must be OWNER.

        Raises:
            ProjectNotFound: If project doesn't exist.
            InsufficientPermissions: If requester is not owner.
        """
        project = await self._repo.get_by_id(ProjectId(project_id))
        requester = project.get_member(UserId(requesting_user_id))
        if not requester or requester.role != ProjectRole.OWNER:
            raise InsufficientPermissions("Only owners can add members")
        project.add_member(UserId(target_user_id), role)
        await self._repo.save(project)
        await self._session.commit()

    async def remove_member(
        self, project_id: str, requesting_user_id: str, target_user_id: str
    ) -> None:
        """Remove a member from a project. Requester must be OWNER."""
        project = await self._repo.get_by_id(ProjectId(project_id))
        requester = project.get_member(UserId(requesting_user_id))
        if not requester or requester.role != ProjectRole.OWNER:
            raise InsufficientPermissions("Only owners can remove members")
        project.members = [
            m for m in project.members if m.user_id != UserId(target_user_id)
        ]
        await self._repo.save(project)
        await self._session.commit()

    async def delete_project(self, project_id: str, requesting_user_id: str) -> None:
        """Delete a project. Requester must be OWNER."""
        project = await self._repo.get_by_id(ProjectId(project_id))
        member = project.get_member(UserId(requesting_user_id))
        if not member or member.role != ProjectRole.OWNER:
            raise InsufficientPermissions("Only owners can delete a project")
        await self._repo.delete(ProjectId(project_id))
        await self._session.commit()


class IssueAppService:
    """Application service for issue management.

    Key difference from the old IssueService:
    - Uses event bus instead of calling NotificationDispatcher directly.
    - Decouples issue_tracking from notifications context.
    """

    def __init__(self, session: AsyncSession, event_bus: EventBus) -> None:
        """Initialize with session and event bus.

        Args:
            session: Database session (shared with event bus handlers).
            event_bus: Request-scoped event bus with notification handler subscribed.
        """
        self._session = session
        self._event_bus = event_bus
        self._issue_repo = PostgresIssueRepository(session)
        self._project_repo = PostgresProjectRepository(session)

    async def create_issue(
        self,
        project_id: str,
        reporter_id: str,
        type: IssueType,
        title: str,
        description: str | None,
        status: IssueStatus,
        priority: Priority,
        parent_id: str | None,
        assignee_id: str | None,
    ) -> Issue:
        """Create a new issue.

        Args:
            project_id: The project this issue belongs to.
            reporter_id: The creating user's ID.
            type: Issue type (task, bug, story, epic).
            title: Issue title.
            description: Optional description.
            status: Initial status.
            priority: Initial priority.
            parent_id: Optional parent issue ID.
            assignee_id: Optional initial assignee.

        Returns:
            Created Issue aggregate.

        Raises:
            ProjectNotFound: If project doesn't exist.
            InsufficientPermissions: If reporter is a VIEWER.
            AssigneeNotProjectMember: If assignee is not in the project.
        """
        project = await self._project_repo.get_by_id(ProjectId(project_id))
        reporter_member = project.get_member(UserId(reporter_id))
        if not reporter_member:
            raise InsufficientPermissions("User is not a project member")
        if reporter_member.role == ProjectRole.VIEWER:
            raise InsufficientPermissions("Viewers cannot create issues")

        if assignee_id:
            assignee_member = project.get_member(UserId(assignee_id))
            if not assignee_member:
                raise AssigneeNotProjectMember(assignee_id)

        issue = Issue(
            issue_id=IssueId(""),  # assigned on flush
            project_id=ProjectId(project_id),
            type=type,
            title=title,
            description=description,
            status=status,
            priority=priority,
            assignee_id=UserId(assignee_id) if assignee_id else None,
            reporter_id=UserId(reporter_id),
            parent_id=IssueId(parent_id) if parent_id else None,
        )
        saved = await self._issue_repo.save(issue)
        await self._session.commit()
        return saved

    async def update_issue(
        self,
        issue_id: str,
        requesting_user_id: str,
        **fields: object,
    ) -> Issue:
        """Update an issue. Emits domain events via event bus.

        Transaction flow:
          1. Load issue and validate membership
          2. Apply field updates (using domain methods for assignee/status)
          3. Save (flush)
          4. Pull events and publish via event bus (handlers flush, no commit)
          5. Single commit — atomic for both issue and side effects

        Args:
            issue_id: The issue UUID.
            requesting_user_id: The user performing the update.
            **fields: Fields to update (title, description, type, status,
                      priority, parent_id, assignee_id).

        Returns:
            Updated Issue aggregate.

        Raises:
            IssueNotFound: If issue doesn't exist or user has no access.
            InsufficientPermissions: If user is a VIEWER.
            AssigneeNotProjectMember: If new assignee is not in the project.
        """
        issue = await self._issue_repo.get_by_id(IssueId(issue_id))
        project = await self._project_repo.get_by_id(issue.project_id)
        member = project.get_member(UserId(requesting_user_id))

        if not member:
            raise IssueNotFound(issue_id)
        if member.role == ProjectRole.VIEWER:
            raise InsufficientPermissions("Viewers cannot modify issues")

        if "assignee_id" in fields and fields["assignee_id"] is not None:
            assignee_id = str(fields["assignee_id"])
            if not project.get_member(UserId(assignee_id)):
                raise AssigneeNotProjectMember(assignee_id)
            issue.assign_to(UserId(assignee_id))
            fields = {k: v for k, v in fields.items() if k != "assignee_id"}

        if "status" in fields and fields["status"] is not None:
            issue.change_status(IssueStatus(str(fields["status"])))
            fields = {k: v for k, v in fields.items() if k != "status"}

        # Apply remaining simple fields
        for field_name, value in fields.items():
            if value is not None:
                setattr(issue, field_name, value)

        saved = await self._issue_repo.save(issue)  # flush only

        # Publish events — handlers run in same session, before commit
        for event in issue.pull_events():
            await self._event_bus.publish(event)

        await self._session.commit()
        return saved

    async def delete_issue(self, issue_id: str, requesting_user_id: str) -> None:
        """Delete an issue. Requester must have MEMBER or OWNER role."""
        issue = await self._issue_repo.get_by_id(IssueId(issue_id))
        project = await self._project_repo.get_by_id(issue.project_id)
        member = project.get_member(UserId(requesting_user_id))

        if not member:
            raise IssueNotFound(issue_id)
        if member.role == ProjectRole.VIEWER:
            raise InsufficientPermissions("Viewers cannot delete issues")

        await self._issue_repo.delete(IssueId(issue_id))
        await self._session.commit()

    async def create_comment(self, issue_id: str, author_id: str, body: str) -> Comment:
        """Add a comment to an issue.

        Loads the issue, adds comment via domain entity, persists via ORM directly
        (Comment is part of Issue aggregate but we avoid loading all comments
        for performance).

        Returns:
            Created Comment entity.
        """
        # Verify issue exists and user has access
        issue = await self._issue_repo.get_by_id(IssueId(issue_id))
        project = await self._project_repo.get_by_id(issue.project_id)
        if not project.get_member(UserId(author_id)):
            raise IssueNotFound(issue_id)

        comment_id = str(uuid.uuid4())
        comment_model = CommentModel(
            comment_id=comment_id,
            issue_id=issue_id,
            author_id=author_id,
            body=body,
        )
        self._session.add(comment_model)
        await self._session.commit()
        await self._session.refresh(comment_model)
        return Comment(
            comment_id=CommentId(comment_model.comment_id),
            issue_id=IssueId(comment_model.issue_id),
            author_id=UserId(comment_model.author_id),
            body=comment_model.body,
            created_at=comment_model.created_at,
        )

    async def list_comments(
        self, issue_id: str, requesting_user_id: str
    ) -> list[Comment]:
        """List comments for an issue.

        Args:
            issue_id: The issue UUID.
            requesting_user_id: Must be a project member.

        Returns:
            List of Comment entities.
        """
        issue = await self._issue_repo.get_by_id(IssueId(issue_id))
        project = await self._project_repo.get_by_id(issue.project_id)
        if not project.get_member(UserId(requesting_user_id)):
            raise IssueNotFound(issue_id)

        result = await self._session.execute(
            select(CommentModel)
            .where(CommentModel.issue_id == issue_id)
            .order_by(CommentModel.created_at)
        )
        return [
            Comment(
                comment_id=CommentId(m.comment_id),
                issue_id=IssueId(m.issue_id),
                author_id=UserId(m.author_id),
                body=m.body,
                created_at=m.created_at,
            )
            for m in result.scalars().all()
        ]
