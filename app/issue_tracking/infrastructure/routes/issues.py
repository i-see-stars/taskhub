"""Issue API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.identity.infrastructure.deps import get_current_user
from app.identity.infrastructure.models import UserModel
from app.issue_tracking.application.issue_use_cases import (
    CreateIssueUseCase,
    DeleteIssueUseCase,
    UpdateIssueUseCase,
)
from app.issue_tracking.domain.exceptions import (
    AssigneeNotProjectMember,
    InsufficientPermissions,
    IssueNotFound,
    ProjectNotFound,
)
from app.issue_tracking.infrastructure.deps import (
    get_create_issue_use_case,
    get_delete_issue_use_case,
    get_update_issue_use_case,
    resolve_issue,
    resolve_issue_list,
)
from app.issue_tracking.infrastructure.models import IssueModel
from app.issue_tracking.infrastructure.schemas import (
    IssueCreate,
    IssueListResponse,
    IssueResponse,
    IssueUpdate,
)

router = APIRouter(tags=["issues"])


@router.get(
    "",
    response_model=IssueListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_issues(
    issues: list[IssueModel] = Depends(resolve_issue_list),
) -> IssueListResponse:
    """List all issues accessible to current user."""
    return IssueListResponse(issues=issues, total=len(issues))


@router.post(
    "",
    response_model=IssueResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_issue(
    issue_data: IssueCreate,
    current_user: UserModel = Depends(get_current_user),
    use_case: CreateIssueUseCase = Depends(get_create_issue_use_case),
) -> IssueResponse:
    """Create a new issue."""
    try:
        issue = await use_case.execute(
            project_id=issue_data.project_id,
            reporter_id=current_user.user_id,
            type=issue_data.type,
            title=issue_data.title,
            description=issue_data.description,
            status=issue_data.status,
            priority=issue_data.priority,
            parent_id=issue_data.parent_id,
            assignee_id=issue_data.assignee_id,
        )
    except ProjectNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from None
    except InsufficientPermissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot create issues",
        ) from None
    except AssigneeNotProjectMember:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee must be a member of the project",
        ) from None
    return IssueResponse(
        issue_id=issue.issue_id.value,
        project_id=issue.project_id.value,
        type=issue.type,
        title=issue.title,
        description=issue.description,
        status=issue.status,
        priority=issue.priority,
        assignee_id=issue.assignee_id.value if issue.assignee_id else None,
        reporter_id=issue.reporter_id.value,
        parent_id=issue.parent_id.value if issue.parent_id else None,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
    )


@router.get(
    "/{issue_id}",
    response_model=IssueResponse,
    status_code=status.HTTP_200_OK,
)
async def get_issue(
    issue: IssueModel = Depends(resolve_issue),
) -> IssueModel:
    """Get issue by ID."""
    return issue


@router.patch(
    "/{issue_id}",
    response_model=IssueResponse,
    status_code=status.HTTP_200_OK,
)
async def update_issue(
    issue_id: str,
    issue_data: IssueUpdate,
    current_user: UserModel = Depends(get_current_user),
    use_case: UpdateIssueUseCase = Depends(get_update_issue_use_case),
) -> IssueResponse:
    """Update issue. Uses UpdateIssueUseCase for domain logic and event bus."""
    update_fields = issue_data.model_dump(exclude_unset=True)
    try:
        issue = await use_case.execute(
            issue_id=issue_id,
            requesting_user_id=current_user.user_id,
            **update_fields,
        )
    except IssueNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found"
        ) from None
    except InsufficientPermissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot modify issues",
        ) from None
    except AssigneeNotProjectMember:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee must be a member of the project",
        ) from None
    return IssueResponse(
        issue_id=issue.issue_id.value,
        project_id=issue.project_id.value,
        type=issue.type,
        title=issue.title,
        description=issue.description,
        status=issue.status,
        priority=issue.priority,
        assignee_id=issue.assignee_id.value if issue.assignee_id else None,
        reporter_id=issue.reporter_id.value,
        parent_id=issue.parent_id.value if issue.parent_id else None,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
    )


@router.delete(
    "/{issue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_issue(
    issue_id: str,
    current_user: UserModel = Depends(get_current_user),
    use_case: DeleteIssueUseCase = Depends(get_delete_issue_use_case),
) -> None:
    """Delete issue. Requires member or owner role."""
    try:
        await use_case.execute(issue_id, current_user.user_id)
    except IssueNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        ) from None
    except InsufficientPermissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot delete issues",
        ) from None
