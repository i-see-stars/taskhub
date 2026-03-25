"""Read-side query functions for issue tracking.

These bypass domain aggregates for read-heavy list operations,
using optimized JOINs to avoid N+1 queries.
Only used for GET list endpoints — write operations go through repositories.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.issue_tracking.infrastructure.models import (
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
