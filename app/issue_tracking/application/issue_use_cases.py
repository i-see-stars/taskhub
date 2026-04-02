"""Issue and comment write use cases.

Each use case is a single-purpose class with one execute() method.
Depends on domain abstractions only (Repository, UnitOfWork, event bus).
"""

from __future__ import annotations

import uuid

from app.core.event_bus import EventBus
from app.issue_tracking.domain.entities import Comment, Issue
from app.issue_tracking.domain.exceptions import (
    AssigneeNotProjectMember,
    CommentDeleteNotPermitted,
    CommentNotFound,
    InsufficientPermissions,
    IssueNotFound,
)
from app.issue_tracking.domain.repositories import IssueRepository, ProjectRepository
from app.issue_tracking.domain.value_objects import (
    IssueStatus,
    IssueType,
    Priority,
    ProjectRole,
)
from app.shared.domain.identifiers import CommentId, IssueId, ProjectId, UserId
from app.shared.domain.unit_of_work import UnitOfWork


class CreateIssueUseCase:
    """Create a new issue in a project."""

    def __init__(
        self,
        issue_repo: IssueRepository,
        project_repo: ProjectRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        """Initialize.

        Args:
            issue_repo: Abstract issue repository.
            project_repo: Abstract project repository.
            unit_of_work: Unit of work for transaction management.
        """
        self._issue_repo = issue_repo
        self._project_repo = project_repo
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        project_id: str,
        reporter_id: str,
        type: IssueType,
        title: str,
        description: str | None,
        status: IssueStatus,
        priority: Priority,
        parent_id: str | None = None,
        assignee_id: str | None = None,
    ) -> Issue:
        """Create issue.

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
            InsufficientPermissions: If reporter is a VIEWER or not a member.
            AssigneeNotProjectMember: If assignee is not a project member.
        """
        project = await self._project_repo.get_by_id(ProjectId(project_id))
        reporter = project.get_member(UserId(reporter_id))
        if not reporter:
            raise InsufficientPermissions("Only project members can create issues")
        if reporter.role == ProjectRole.VIEWER:
            raise InsufficientPermissions("Viewers cannot create issues")
        if assignee_id and not project.get_member(UserId(assignee_id)):
            raise AssigneeNotProjectMember(assignee_id)

        issue = Issue(
            issue_id=IssueId(str(uuid.uuid4())),
            project_id=ProjectId(project_id),
            type=type,
            title=title,
            description=description,
            status=status,
            priority=priority,
            reporter_id=UserId(reporter_id),
            assignee_id=UserId(assignee_id) if assignee_id else None,
            parent_id=IssueId(parent_id) if parent_id else None,
        )
        saved = await self._issue_repo.save(issue)
        await self._unit_of_work.commit()
        return saved


class UpdateIssueUseCase:
    """Update issue fields and publish domain events."""

    def __init__(
        self,
        issue_repo: IssueRepository,
        project_repo: ProjectRepository,
        unit_of_work: UnitOfWork,
        event_bus: EventBus,
    ) -> None:
        """Initialize.

        Args:
            issue_repo: Abstract issue repository.
            project_repo: Abstract project repository.
            unit_of_work: Unit of work for transaction management.
            event_bus: Event bus for publishing domain events.
        """
        self._issue_repo = issue_repo
        self._project_repo = project_repo
        self._unit_of_work = unit_of_work
        self._event_bus = event_bus

    async def execute(
        self,
        issue_id: str,
        requesting_user_id: str,
        **fields: object,
    ) -> Issue:
        """Update issue, emit IssueAssigned / IssueStatusChanged events.

        Args:
            issue_id: The issue UUID.
            requesting_user_id: The user performing the update.
            **fields: Fields to update (title, description, type, status,
                      priority, parent_id, assignee_id).

        Returns:
            Updated Issue aggregate.

        Raises:
            IssueNotFound: If issue doesn't exist or user has no access.
            InsufficientPermissions: If requester is VIEWER.
            AssigneeNotProjectMember: If new assignee is not a project member.
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

        for field_name, value in fields.items():
            if value is not None:
                setattr(issue, field_name, value)

        saved = await self._issue_repo.save(issue)
        for event in issue.pull_events():
            await self._event_bus.publish(event)
        await self._unit_of_work.commit()
        return saved


class DeleteIssueUseCase:
    """Delete an issue. Requester must be a non-VIEWER project member."""

    def __init__(
        self,
        issue_repo: IssueRepository,
        project_repo: ProjectRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        """Initialize.

        Args:
            issue_repo: Abstract issue repository.
            project_repo: Abstract project repository.
            unit_of_work: Unit of work for transaction management.
        """
        self._issue_repo = issue_repo
        self._project_repo = project_repo
        self._unit_of_work = unit_of_work

    async def execute(self, issue_id: str, requesting_user_id: str) -> None:
        """Delete issue.

        Args:
            issue_id: The issue UUID.
            requesting_user_id: The user performing the deletion.

        Raises:
            IssueNotFound: If issue doesn't exist or user has no access.
            InsufficientPermissions: If requester is VIEWER.
        """
        issue = await self._issue_repo.get_by_id(IssueId(issue_id))
        project = await self._project_repo.get_by_id(issue.project_id)
        member = project.get_member(UserId(requesting_user_id))
        if not member:
            raise IssueNotFound(issue_id)
        if member.role == ProjectRole.VIEWER:
            raise InsufficientPermissions("Viewers cannot delete issues")
        await self._issue_repo.delete(IssueId(issue_id))
        await self._unit_of_work.commit()


class CreateCommentUseCase:
    """Add a comment to an issue via the Issue aggregate."""

    def __init__(
        self,
        issue_repo: IssueRepository,
        project_repo: ProjectRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        """Initialize.

        Args:
            issue_repo: Abstract issue repository.
            project_repo: Abstract project repository.
            unit_of_work: Unit of work for transaction management.
        """
        self._issue_repo = issue_repo
        self._project_repo = project_repo
        self._unit_of_work = unit_of_work

    async def execute(self, issue_id: str, author_id: str, body: str) -> Comment:
        """Add comment.

        Args:
            issue_id: The issue UUID.
            author_id: The commenting user's ID.
            body: Comment text.

        Returns:
            The new Comment entity.

        Raises:
            IssueNotFound: If issue doesn't exist or user has no access.
            InsufficientPermissions: If author is VIEWER.
        """
        issue = await self._issue_repo.get_with_comments(IssueId(issue_id))
        project = await self._project_repo.get_by_id(issue.project_id)
        member = project.get_member(UserId(author_id))
        if not member:
            raise IssueNotFound(issue_id)
        if member.role == ProjectRole.VIEWER:
            raise InsufficientPermissions("Viewers cannot add comments")

        comment = issue.add_comment(
            comment_id=CommentId(str(uuid.uuid4())),
            author_id=UserId(author_id),
            body=body,
        )
        await self._issue_repo.save(issue)
        await self._unit_of_work.commit()
        # Re-fetch to get DB-generated timestamps
        saved_issue = await self._issue_repo.get_with_comments(IssueId(issue_id))
        saved_comment = next(
            (c for c in saved_issue.comments if c.comment_id == comment.comment_id),
            comment,
        )
        return saved_comment


class DeleteCommentUseCase:
    """Delete a comment via the Issue aggregate. Only author or OWNER."""

    def __init__(
        self,
        issue_repo: IssueRepository,
        project_repo: ProjectRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        """Initialize.

        Args:
            issue_repo: Abstract issue repository.
            project_repo: Abstract project repository.
            unit_of_work: Unit of work for transaction management.
        """
        self._issue_repo = issue_repo
        self._project_repo = project_repo
        self._unit_of_work = unit_of_work

    async def execute(
        self, issue_id: str, comment_id: str, requesting_user_id: str
    ) -> None:
        """Delete comment.

        Args:
            issue_id: The issue UUID.
            comment_id: The comment UUID.
            requesting_user_id: The user requesting deletion.

        Raises:
            IssueNotFound: If issue doesn't exist or user has no access.
            CommentNotFound: If comment doesn't exist on this issue.
            CommentDeleteNotPermitted: If user is not author or OWNER.
        """
        issue = await self._issue_repo.get_with_comments(IssueId(issue_id))
        project = await self._project_repo.get_by_id(issue.project_id)
        member = project.get_member(UserId(requesting_user_id))
        if not member:
            raise IssueNotFound(issue_id)

        comment = next(
            (c for c in issue.comments if c.comment_id == CommentId(comment_id)),
            None,
        )
        if not comment:
            raise CommentNotFound(f"Comment {comment_id!r} not found")

        is_author = comment.author_id == UserId(requesting_user_id)
        is_owner = member.role == ProjectRole.OWNER
        if not is_author and not is_owner:
            raise CommentDeleteNotPermitted(
                "Only the comment author or project owner can delete"
            )

        issue.comments = [
            c for c in issue.comments if c.comment_id != CommentId(comment_id)
        ]
        await self._issue_repo.save(issue)
        await self._unit_of_work.commit()
