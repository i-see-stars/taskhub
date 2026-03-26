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
    CommentRepository,
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
            select(ProjectModel).where(
                ProjectModel.project_id == project.project_id.value
            )
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
        else:
            model.name = project.name
            model.key = project.key
            model.description = project.description

        # Sync members: delete removed, add new
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
                # Update role if changed
                for m in model.members:
                    if m.user_id == dm.user_id.value:
                        m.role = dm.role

        await self.session.flush()
        # Reload with members
        await self.session.refresh(model)
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

    async def save(self, issue: Issue) -> Issue:
        """Persist new or updated issue (without comments)."""
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


class PostgresCommentRepository(CommentRepository):
    """Comment repository backed by PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session.

        Args:
            session: The async database session.
        """
        self.session = session

    async def save(self, comment: Comment) -> Comment:
        """Persist a new comment.

        Args:
            comment: The Comment domain entity.

        Returns:
            The saved Comment with DB-assigned fields populated.
        """
        model = CommentModel(
            comment_id=comment.comment_id.value,
            issue_id=comment.issue_id.value,
            author_id=comment.author_id.value,
            body=comment.body,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return Comment(
            comment_id=CommentId(model.comment_id),
            issue_id=IssueId(model.issue_id),
            author_id=UserId(model.author_id),
            body=model.body,
            created_at=model.created_at,
        )

    async def list_for_issue(self, issue_id: object) -> list[Comment]:
        """List all comments for an issue, ordered by creation time.

        Args:
            issue_id: The issue identifier.

        Returns:
            List of Comment entities.
        """
        iid = issue_id if isinstance(issue_id, IssueId) else IssueId(str(issue_id))
        result = await self.session.execute(
            select(CommentModel)
            .where(CommentModel.issue_id == iid.value)
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
