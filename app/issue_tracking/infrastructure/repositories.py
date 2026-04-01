"""PostgreSQL implementations of issue tracking repositories."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.issue_tracking.domain.entities import (
    Comment,
    Issue,
    Project,
    ProjectMember,
)
from app.issue_tracking.domain.exceptions import IssueNotFound, ProjectNotFound
from app.issue_tracking.domain.repositories import (
    IssueRepository,
    ProjectRepository,
)
from app.issue_tracking.domain.value_objects import (
    IssueStatus,
    IssueType,
    Priority,
    ProjectRole,
)
from app.issue_tracking.infrastructure.models import (
    CommentModel,
    IssueModel,
    ProjectMemberModel,
    ProjectModel,
)
from app.shared.domain.identifiers import (
    CommentId,
    IssueId,
    ProjectId,
    UserId,
)


class PostgresProjectRepository(ProjectRepository):
    """Project repository backed by PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        self.session = session

    def _member_to_domain(self, m: ProjectMemberModel) -> ProjectMember:
        """Map ORM member model to domain entity.

        Args:
            m: The ORM member model.

        Returns:
            Domain ProjectMember entity.
        """
        return ProjectMember(
            project_id=ProjectId(m.project_id),
            user_id=UserId(m.user_id),
            role=ProjectRole(m.role),
            created_at=m.created_at,
        )

    def _to_domain(self, model: ProjectModel) -> Project:
        """Map ORM project model to domain aggregate.

        Args:
            model: The ORM project model.

        Returns:
            Domain Project aggregate.
        """
        return Project(
            project_id=ProjectId(model.project_id),
            name=model.name,
            key=model.key,
            description=model.description,
            members=[self._member_to_domain(m) for m in model.members],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def get_by_id(self, project_id: object) -> Project:
        """Fetch project with members. Raises ProjectNotFound if absent."""
        pid = (
            project_id
            if isinstance(project_id, ProjectId)
            else ProjectId(str(project_id))
        )
        result = await self.session.execute(
            select(ProjectModel)
            .options(selectinload(ProjectModel.members))
            .where(ProjectModel.project_id == pid.value)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ProjectNotFound(f"Project {pid.value!r} not found")
        return self._to_domain(model)

    async def save(self, project: Project) -> Project:
        """Persist new or updated project."""
        result = await self.session.execute(
            select(ProjectModel)
            .options(selectinload(ProjectModel.members))
            .where(ProjectModel.project_id == project.project_id.value)
        )
        model = result.scalar_one_or_none()
        if model is None:
            model = ProjectModel(
                project_id=project.project_id.value,
                name=project.name,
                key=project.key,
                description=project.description,
            )
            self.session.add(model)
            await self.session.flush()
            # New model has no members yet — just add all
            for dm in project.members:
                self.session.add(
                    ProjectMemberModel(
                        project_id=model.project_id,
                        user_id=dm.user_id.value,
                        role=dm.role,
                    )
                )
        else:
            model.name = project.name
            model.key = project.key
            model.description = project.description

            # Sync members: delete removed, add new, update existing
            existing_ids = {m.user_id for m in model.members}
            domain_ids = {m.user_id.value for m in project.members}
            for m in list(model.members):
                if m.user_id not in domain_ids:
                    await self.session.delete(m)
            for dm in project.members:
                if dm.user_id.value not in existing_ids:
                    self.session.add(
                        ProjectMemberModel(
                            project_id=model.project_id,
                            user_id=dm.user_id.value,
                            role=dm.role,
                        )
                    )
                else:
                    for m in model.members:
                        if m.user_id == dm.user_id.value:
                            m.role = dm.role

        await self.session.flush()
        # Full reload including relationships
        await self.session.refresh(model)
        # Eagerly load members to avoid lazy-load in async
        result = await self.session.execute(
            select(ProjectModel)
            .options(selectinload(ProjectModel.members))
            .where(ProjectModel.project_id == model.project_id)
        )
        model = result.scalar_one()
        return self._to_domain(model)

    async def list_for_user(self, user_id: object) -> list[Project]:
        """List all projects the given user is a member of."""
        uid = user_id if isinstance(user_id, UserId) else UserId(str(user_id))
        result = await self.session.execute(
            select(ProjectModel)
            .options(selectinload(ProjectModel.members))
            .join(ProjectMemberModel)
            .where(ProjectMemberModel.user_id == uid.value)
        )
        return [self._to_domain(m) for m in result.scalars().all()]

    async def delete(self, project_id: object) -> None:
        """Delete project by ID."""
        pid = (
            project_id
            if isinstance(project_id, ProjectId)
            else ProjectId(str(project_id))
        )
        result = await self.session.execute(
            select(ProjectModel).where(ProjectModel.project_id == pid.value)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)

    async def key_exists(self, key: str) -> bool:
        """Check if a project with this key already exists.

        Args:
            key: The project key to check.

        Returns:
            True if a project with this key exists.
        """
        result = await self.session.execute(
            select(ProjectModel).where(ProjectModel.key == key)
        )
        return result.scalar_one_or_none() is not None


class PostgresIssueRepository(IssueRepository):
    """Issue repository backed by PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        self.session = session

    def _to_domain(self, model: IssueModel) -> Issue:
        """Map ORM issue model to domain aggregate.

        Args:
            model: The ORM issue model.

        Returns:
            Domain Issue aggregate.
        """
        return Issue(
            issue_id=IssueId(model.issue_id),
            project_id=ProjectId(model.project_id),
            type=IssueType(model.type),
            title=model.title,
            description=model.description,
            status=IssueStatus(model.status),
            priority=Priority(model.priority),
            assignee_id=UserId(model.assignee_id) if model.assignee_id else None,
            reporter_id=UserId(model.reporter_id),
            parent_id=IssueId(model.parent_id) if model.parent_id else None,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Issue) -> IssueModel:
        """Map domain issue to ORM model (for new issues).

        Args:
            entity: The domain Issue aggregate.

        Returns:
            ORM IssueModel.
        """
        return IssueModel(
            issue_id=entity.issue_id.value,
            project_id=entity.project_id.value,
            type=entity.type,
            title=entity.title,
            description=entity.description,
            status=entity.status,
            priority=entity.priority,
            assignee_id=entity.assignee_id.value if entity.assignee_id else None,
            reporter_id=entity.reporter_id.value,
            parent_id=entity.parent_id.value if entity.parent_id else None,
        )

    def _comment_to_domain(self, model: CommentModel) -> Comment:
        """Map ORM comment model to domain entity.

        Args:
            model: The ORM comment model.

        Returns:
            Domain Comment entity.
        """
        return Comment(
            comment_id=CommentId(model.comment_id),
            issue_id=IssueId(model.issue_id),
            author_id=UserId(model.author_id),
            body=model.body,
            created_at=model.created_at,
        )

    async def get_by_id(self, issue_id: object) -> Issue:
        """Fetch issue. Raises IssueNotFound if absent."""
        iid = issue_id if isinstance(issue_id, IssueId) else IssueId(str(issue_id))
        result = await self.session.execute(
            select(IssueModel).where(IssueModel.issue_id == iid.value)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise IssueNotFound(f"Issue {iid.value!r} not found")
        return self._to_domain(model)

    async def get_with_comments(self, issue_id: object) -> Issue:
        """Fetch issue with comments loaded. Raises IssueNotFound if absent.

        Args:
            issue_id: The issue identifier.

        Returns:
            Issue aggregate with comments populated.

        Raises:
            IssueNotFound: If issue doesn't exist.
        """
        iid = issue_id if isinstance(issue_id, IssueId) else IssueId(str(issue_id))
        result = await self.session.execute(
            select(IssueModel)
            .options(selectinload(IssueModel.comments))
            .where(IssueModel.issue_id == iid.value)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise IssueNotFound(f"Issue {iid.value!r} not found")
        issue = self._to_domain(model)
        issue.comments = [self._comment_to_domain(c) for c in model.comments]
        return issue

    async def save(self, issue: Issue) -> Issue:
        """Persist new or updated issue, syncing comments.

        Args:
            issue: The Issue aggregate to persist.

        Returns:
            The saved Issue (without comments — use get_with_comments for that).
        """
        result = await self.session.execute(
            select(IssueModel).where(IssueModel.issue_id == issue.issue_id.value)
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            model = self._to_model(issue)
            self.session.add(model)
        else:
            existing.title = issue.title
            existing.description = issue.description
            existing.type = issue.type
            existing.status = issue.status
            existing.priority = issue.priority
            existing.assignee_id = (
                issue.assignee_id.value if issue.assignee_id else None
            )
            existing.parent_id = issue.parent_id.value if issue.parent_id else None
            model = existing

        # Sync comments: add new, remove deleted
        if issue.comments:
            existing_comments_result = await self.session.execute(
                select(CommentModel).where(
                    CommentModel.issue_id == issue.issue_id.value
                )
            )
            existing_comment_ids = {
                c.comment_id for c in existing_comments_result.scalars().all()
            }
            domain_comment_ids = {c.comment_id.value for c in issue.comments}

            # Delete removed comments
            for cid in existing_comment_ids - domain_comment_ids:
                del_result = await self.session.execute(
                    select(CommentModel).where(CommentModel.comment_id == cid)
                )
                del_model = del_result.scalar_one_or_none()
                if del_model:
                    await self.session.delete(del_model)

            # Add new comments
            for comment in issue.comments:
                if comment.comment_id.value not in existing_comment_ids:
                    self.session.add(
                        CommentModel(
                            comment_id=comment.comment_id.value,
                            issue_id=issue.issue_id.value,
                            author_id=comment.author_id.value,
                            body=comment.body,
                        )
                    )

        await self.session.flush()
        await self.session.refresh(model)
        return self._to_domain(model)

    async def delete(self, issue_id: object) -> None:
        """Delete issue by ID."""
        iid = issue_id if isinstance(issue_id, IssueId) else IssueId(str(issue_id))
        result = await self.session.execute(
            select(IssueModel).where(IssueModel.issue_id == iid.value)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
