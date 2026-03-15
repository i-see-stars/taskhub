"""Issue API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.dependencies import get_current_user
from app.api.auth.models import User
from app.api.core.database import get_session
from app.api.issues.models import Issue
from app.api.issues.schemas import (
    IssueCreate,
    IssueListResponse,
    IssueResponse,
    IssueUpdate,
)
from app.api.projects.models import Project

router = APIRouter(prefix="/issues", tags=["issues"])


@router.get("", response_model=IssueListResponse)
async def list_issues(
    project_id: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> IssueListResponse:
    """List all issues for current user (optionally filtered by project)."""
    query = select(Issue).join(Project).where(Project.owner_id == current_user.user_id)

    if project_id:
        query = query.where(Issue.project_id == project_id)

    result = await session.execute(query)
    issues = result.scalars().all()
    return IssueListResponse(issues=issues, total=len(issues))


@router.post("", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
async def create_issue(
    issue_data: IssueCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Issue:
    """Create a new issue."""
    # Verify project exists and user owns it
    project_result = await session.execute(
        select(Project).where(
            Project.project_id == issue_data.project_id,
            Project.owner_id == current_user.user_id,
        )
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Verify parent issue exists if provided
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
        .join(Project)
        .where(
            Issue.issue_id == issue_id,
            Project.owner_id == current_user.user_id,
        )
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
) -> Issue:
    """Update issue."""
    result = await session.execute(
        select(Issue)
        .join(Project)
        .where(
            Issue.issue_id == issue_id,
            Project.owner_id == current_user.user_id,
        )
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    # Update fields
    for field, value in issue_data.model_dump(exclude_unset=True).items():
        setattr(issue, field, value)

    await session.commit()
    await session.refresh(issue)
    return issue


@router.delete("/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_issue(
    issue_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete issue."""
    result = await session.execute(
        select(Issue)
        .join(Project)
        .where(
            Issue.issue_id == issue_id,
            Project.owner_id == current_user.user_id,
        )
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    await session.delete(issue)
    await session.commit()
