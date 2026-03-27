"""Read-side query functions for issue tracking.

These bypass domain aggregates for read-heavy list operations,
using optimized JOINs to avoid N+1 queries.
Only used for GET list endpoints — write operations go through repositories.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.issue_tracking.infrastructure.models import (
    CommentModel,
    IssueModel,
    ProjectMemberModel,
    ProjectModel,
)


async def list_projects_for_user(
    session: AsyncSession,
    user_id: str,
) -> list[ProjectModel]:
    """List projects a user is a member of.

    Args:
        session: Database session.
        user_id: The user's ID string.

    Returns:
        List of ProjectModel rows.
    """
    result = await session.execute(
        select(ProjectModel)
        .join(ProjectMemberModel)
        .where(ProjectMemberModel.user_id == user_id)
    )
    return list(result.scalars().all())


async def list_issues_for_user(
    session: AsyncSession,
    user_id: str,
    project_id: str | None = None,
) -> list[IssueModel]:
    """List issues accessible to user (optionally filtered by project).

    Uses a JOIN to project membership for access control.

    Args:
        session: Database session.
        user_id: The requesting user's ID.
        project_id: Optional project filter.

    Returns:
        List of IssueModel rows.
    """
    query = (
        select(IssueModel)
        .join(ProjectModel, IssueModel.project_id == ProjectModel.project_id)
        .join(
            ProjectMemberModel,
            (ProjectMemberModel.project_id == ProjectModel.project_id)
            & (ProjectMemberModel.user_id == user_id),
        )
    )
    if project_id:
        query = query.where(IssueModel.project_id == project_id)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_project_by_id(
    session: AsyncSession,
    project_id: str,
    user_id: str,
) -> ProjectModel | None:
    """Get project if user is a member. Returns None if not found or no access.

    Args:
        session: Database session.
        project_id: The project UUID.
        user_id: The requesting user's ID.

    Returns:
        ProjectModel if found and accessible, None otherwise.
    """
    result = await session.execute(
        select(ProjectModel)
        .join(
            ProjectMemberModel,
            (ProjectMemberModel.project_id == ProjectModel.project_id)
            & (ProjectMemberModel.user_id == user_id),
        )
        .where(ProjectModel.project_id == project_id)
    )
    return result.scalar_one_or_none()


async def list_members_for_project(
    session: AsyncSession,
    project_id: str,
    user_id: str,
) -> list[ProjectMemberModel] | None:
    """List members if user is a member. Returns None if no access.

    Args:
        session: Database session.
        project_id: The project UUID.
        user_id: The requesting user's ID.

    Returns:
        List of ProjectMemberModel if accessible, None otherwise.
    """
    member_check = await session.execute(
        select(ProjectMemberModel).where(
            ProjectMemberModel.project_id == project_id,
            ProjectMemberModel.user_id == user_id,
        )
    )
    if not member_check.scalar_one_or_none():
        return None

    result = await session.execute(
        select(ProjectMemberModel).where(ProjectMemberModel.project_id == project_id)
    )
    return list(result.scalars().all())


async def get_issue_by_id(
    session: AsyncSession,
    issue_id: str,
    user_id: str,
) -> IssueModel | None:
    """Get issue if user is a member of its project. Returns None if not found.

    Args:
        session: Database session.
        issue_id: The issue UUID.
        user_id: The requesting user's ID.

    Returns:
        IssueModel if found and accessible, None otherwise.
    """
    result = await session.execute(
        select(IssueModel)
        .join(ProjectModel, IssueModel.project_id == ProjectModel.project_id)
        .join(
            ProjectMemberModel,
            (ProjectMemberModel.project_id == ProjectModel.project_id)
            & (ProjectMemberModel.user_id == user_id),
        )
        .where(IssueModel.issue_id == issue_id)
    )
    return result.scalar_one_or_none()


async def list_comments_for_issue(
    session: AsyncSession,
    issue_id: str,
    user_id: str,
) -> list[CommentModel] | None:
    """List comments for issue if user has access. Returns None if no access.

    Args:
        session: Database session.
        issue_id: The issue UUID.
        user_id: The requesting user's ID.

    Returns:
        List of CommentModel if accessible, None otherwise.
    """
    issue_result = await session.execute(
        select(IssueModel).where(IssueModel.issue_id == issue_id)
    )
    issue = issue_result.scalar_one_or_none()
    if not issue:
        return None

    member_result = await session.execute(
        select(ProjectMemberModel).where(
            ProjectMemberModel.project_id == issue.project_id,
            ProjectMemberModel.user_id == user_id,
        )
    )
    if not member_result.scalar_one_or_none():
        return None

    result = await session.execute(
        select(CommentModel)
        .where(CommentModel.issue_id == issue_id)
        .order_by(CommentModel.created_at)
    )
    return list(result.scalars().all())
