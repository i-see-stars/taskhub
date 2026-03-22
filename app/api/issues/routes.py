"""Issue API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.deps import get_current_user
from app.api.auth.models import User
from app.api.core.database import get_session
from app.api.issues.models import Issue
from app.api.issues.schemas import (
    IssueCreate,
    IssueListResponse,
    IssueResponse,
    IssueUpdate,
)
from app.api.issues.services import IssueService
from app.api.notifications.deps import get_notification_dispatcher
from app.api.notifications.services import NotificationDispatcher
from app.api.projects.models import Project, ProjectMember, ProjectMemberRole

router = APIRouter(prefix="/issues", tags=["issues"])


async def _require_project_member(
    project_id: str,
    session: AsyncSession,
    current_user: User,
) -> ProjectMember:
    """Verify the current user is a member of the given project.

    Args:
        project_id: The project UUID.
        session: Database session.
        current_user: The authenticated user.

    Returns:
        The user's ProjectMember record.

    Raises:
        HTTPException: 404 if project not found, 403 if user is not a member.
    """
    project_result = await session.execute(
        select(Project).where(Project.project_id == project_id)
    )
    if not project_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    member_result = await session.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.user_id,
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return member


async def _validate_assignee(
    assignee_id: str,
    project_id: str,
    session: AsyncSession,
) -> None:
    """Validate that the assignee is a member of the project.

    Args:
        assignee_id: The user ID to assign.
        project_id: The project UUID.
        session: Database session.

    Raises:
        HTTPException: 400 if assignee is not a project member.
    """
    member_result = await session.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == assignee_id,
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee must be a member of the project",
        )


@router.get("", response_model=IssueListResponse)
async def list_issues(
    project_id: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> IssueListResponse:
    """List all issues accessible to current user (optionally filtered by project)."""
    query = (
        select(Issue)
        .join(Project, Issue.project_id == Project.project_id)
        .join(
            ProjectMember,
            (ProjectMember.project_id == Project.project_id)
            & (ProjectMember.user_id == current_user.user_id),
        )
    )

    if project_id:
        query = query.where(Issue.project_id == project_id)

    result = await session.execute(query)
    issues = result.scalars().all()
    return IssueListResponse(issues=list(issues), total=len(issues))


@router.post("", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
async def create_issue(
    issue_data: IssueCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Issue:
    """Create a new issue."""
    member = await _require_project_member(issue_data.project_id, session, current_user)

    if member.role == ProjectMemberRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot create issues",
        )

    # Validate parent issue belongs to the same project
    if issue_data.parent_id:
        parent_result = await session.execute(
            select(Issue).where(
                Issue.issue_id == issue_data.parent_id,
                Issue.project_id == issue_data.project_id,
            )
        )
        if not parent_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent issue not found",
            )

    # Validate assignee is a project member
    if issue_data.assignee_id:
        await _validate_assignee(issue_data.assignee_id, issue_data.project_id, session)

    issue = Issue(
        **issue_data.model_dump(),
        reporter_id=current_user.user_id,
    )
    session.add(issue)
    await session.commit()
    await session.refresh(issue)
    return issue


@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(
    issue_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Issue:
    """Get issue by ID."""
    result = await session.execute(
        select(Issue)
        .join(Project, Issue.project_id == Project.project_id)
        .join(
            ProjectMember,
            (ProjectMember.project_id == Project.project_id)
            & (ProjectMember.user_id == current_user.user_id),
        )
        .where(Issue.issue_id == issue_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )
    return issue


@router.patch("/{issue_id}", response_model=IssueResponse)
async def update_issue(
    issue_id: str,
    issue_data: IssueUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> Issue:
    """Update issue. Requires member or owner role."""
    service = IssueService(session=session, dispatcher=dispatcher)
    return await service.update_issue(issue_id, issue_data, current_user)


@router.delete("/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_issue(
    issue_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete issue. Requires member or owner role."""
    result = await session.execute(
        select(Issue)
        .join(Project, Issue.project_id == Project.project_id)
        .join(
            ProjectMember,
            (ProjectMember.project_id == Project.project_id)
            & (ProjectMember.user_id == current_user.user_id),
        )
        .where(Issue.issue_id == issue_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    member_result = await session.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == issue.project_id,
            ProjectMember.user_id == current_user.user_id,
        )
    )
    member = member_result.scalar_one_or_none()
    if member and member.role == ProjectMemberRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot delete issues",
        )

    await session.delete(issue)
    await session.commit()
