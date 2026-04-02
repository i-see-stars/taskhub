"""Comment API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.identity.infrastructure.deps import get_current_user
from app.identity.infrastructure.models import UserModel
from app.issue_tracking.application.issue_use_cases import (
    CreateCommentUseCase,
    DeleteCommentUseCase,
)
from app.issue_tracking.domain.exceptions import (
    CommentDeleteNotPermitted,
    CommentNotFound,
    InsufficientPermissions,
    IssueNotFound,
)
from app.issue_tracking.infrastructure.deps import (
    get_create_comment_use_case,
    get_delete_comment_use_case,
    resolve_comment_list,
)
from app.issue_tracking.infrastructure.models import CommentModel
from app.issue_tracking.infrastructure.schemas import (
    CommentCreate,
    CommentListResponse,
    CommentResponse,
)

router = APIRouter(prefix="/issues/{issue_id}/comments", tags=["comments"])


@router.get("", response_model=CommentListResponse)
async def list_comments(
    comments: list[CommentModel] = Depends(resolve_comment_list),
) -> CommentListResponse:
    """List all comments on an issue."""
    return CommentListResponse(comments=list(comments), total=len(comments))


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    issue_id: str,
    comment_data: CommentCreate,
    current_user: UserModel = Depends(get_current_user),
    use_case: CreateCommentUseCase = Depends(get_create_comment_use_case),
) -> CommentResponse:
    """Create a comment on an issue. Requires member or owner role."""
    try:
        comment = await use_case.execute(
            issue_id=issue_id,
            author_id=current_user.user_id,
            body=comment_data.body,
        )
    except IssueNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        ) from None
    except InsufficientPermissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot add comments",
        ) from None
    return CommentResponse(
        comment_id=comment.comment_id.value,
        issue_id=comment.issue_id.value,
        author_id=comment.author_id.value,
        body=comment.body,
        created_at=comment.created_at,
        updated_at=comment.created_at,
    )


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    issue_id: str,
    comment_id: str,
    current_user: UserModel = Depends(get_current_user),
    use_case: DeleteCommentUseCase = Depends(get_delete_comment_use_case),
) -> None:
    """Delete a comment. Only the author or a project owner can delete."""
    try:
        await use_case.execute(
            issue_id=issue_id,
            comment_id=comment_id,
            requesting_user_id=current_user.user_id,
        )
    except IssueNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        ) from None
    except CommentNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        ) from None
    except CommentDeleteNotPermitted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the comment author or project owner can delete comments",
        ) from None
