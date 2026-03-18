"""Comment API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.deps import get_current_user
from app.api.auth.models import User
from app.api.comments.models import Comment
from app.api.comments.schemas import CommentCreate, CommentListResponse, CommentResponse
from app.api.core.database import get_session
from app.api.issues.models import Issue
from app.api.projects.models import ProjectMember, ProjectMemberRole

router = APIRouter(prefix="/issues/{issue_id}/comments", tags=["comments"])


async def _get_issue_and_member(
    issue_id: str,
    session: AsyncSession,
    current_user: User,
) -> tuple[Issue, ProjectMember]:
    """Get issue and verify user is a member of its project.

    Args:
        issue_id: The issue UUID.
        session: Database session.
        current_user: The authenticated user.

    Returns:
        Tuple of (Issue, ProjectMember).

    Raises:
        HTTPException: 404 if issue not found, 403 if user is not a project member.
    """
    issue_result = await session.execute(
        select(Issue).where(Issue.issue_id == issue_id)
    )
    issue = issue_result.scalar_one_or_none()
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
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return issue, member


@router.get("", response_model=CommentListResponse)
async def list_comments(
    issue_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CommentListResponse:
    """List all comments on an issue."""
    await _get_issue_and_member(issue_id, session, current_user)

    result = await session.execute(select(Comment).where(Comment.issue_id == issue_id))
    comments = result.scalars().all()
    return CommentListResponse(comments=list(comments), total=len(comments))


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    issue_id: str,
    comment_data: CommentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Comment:
    """Create a comment on an issue. Requires member or owner role."""
    _, member = await _get_issue_and_member(issue_id, session, current_user)

    if member.role == ProjectMemberRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot add comments",
        )

    comment = Comment(
        issue_id=issue_id,
        author_id=current_user.user_id,
        body=comment_data.body,
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    return comment


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    issue_id: str,
    comment_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a comment. Only the author or a project owner can delete."""
    _, member = await _get_issue_and_member(issue_id, session, current_user)

    comment_result = await session.execute(
        select(Comment).where(
            Comment.comment_id == comment_id,
            Comment.issue_id == issue_id,
        )
    )
    comment = comment_result.scalar_one_or_none()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    is_author = comment.author_id == current_user.user_id
    is_owner = member.role == ProjectMemberRole.OWNER

    if not is_author and not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the comment author or project owner can delete comments",
        )

    await session.delete(comment)
    await session.commit()
