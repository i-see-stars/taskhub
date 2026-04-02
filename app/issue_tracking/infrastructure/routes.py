"""Issue tracking API routes (projects + issues)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.identity.infrastructure.deps import get_current_user
from app.identity.infrastructure.models import UserModel
from app.issue_tracking.application.issue_use_cases import (
    CreateIssueUseCase,
    DeleteIssueUseCase,
    UpdateIssueUseCase,
)
from app.issue_tracking.application.project_use_cases import (
    AddProjectMemberUseCase,
    CreateProjectUseCase,
    DeleteProjectUseCase,
    RemoveProjectMemberUseCase,
    UpdateMemberRoleUseCase,
    UpdateProjectUseCase,
)
from app.issue_tracking.domain.exceptions import (
    AssigneeNotProjectMember,
    DuplicateProjectKey,
    InsufficientPermissions,
    IssueNotFound,
    LastOwnerCannotBeRemoved,
    MemberNotFound,
    ProjectNotFound,
    UserAlreadyProjectMember,
)
from app.issue_tracking.infrastructure.deps import (
    get_add_project_member_use_case,
    get_create_issue_use_case,
    get_create_project_use_case,
    get_delete_issue_use_case,
    get_delete_project_use_case,
    get_remove_project_member_use_case,
    get_update_issue_use_case,
    get_update_member_role_use_case,
    get_update_project_use_case,
    resolve_issue,
    resolve_issue_list,
    resolve_project,
    resolve_project_list,
    resolve_project_members,
)
from app.issue_tracking.infrastructure.models import (
    IssueModel,
    ProjectMemberModel,
    ProjectModel,
)
from app.issue_tracking.infrastructure.schemas import (
    IssueCreate,
    IssueListResponse,
    IssueResponse,
    IssueUpdate,
    ProjectCreate,
    ProjectListResponse,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectMembersListResponse,
    ProjectMemberUpdate,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter()


# ---- Project endpoints ----


@router.get("/projects", response_model=ProjectListResponse, tags=["projects"])
async def list_projects(
    projects: list[ProjectModel] = Depends(resolve_project_list),
) -> ProjectListResponse:
    """List all projects the current user is a member of."""
    return ProjectListResponse(projects=projects, total=len(projects))


@router.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["projects"],
)
async def create_project(
    project_data: ProjectCreate,
    current_user: UserModel = Depends(get_current_user),
    use_case: CreateProjectUseCase = Depends(get_create_project_use_case),
) -> ProjectResponse:
    """Create a new project and add creator as owner."""
    try:
        project = await use_case.execute(
            owner_id=current_user.user_id,
            name=project_data.name,
            key=project_data.key,
            description=project_data.description,
        )
    except DuplicateProjectKey:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project with this key already exists",
        ) from None
    return ProjectResponse(
        project_id=project.project_id.value,
        name=project.name,
        key=project.key,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse, tags=["projects"])
async def get_project(
    project: ProjectModel = Depends(resolve_project),
) -> ProjectModel:
    """Get project by ID."""
    return project


@router.patch(
    "/projects/{project_id}", response_model=ProjectResponse, tags=["projects"]
)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    current_user: UserModel = Depends(get_current_user),
    use_case: UpdateProjectUseCase = Depends(get_update_project_use_case),
) -> ProjectResponse:
    """Update project. Requires member or owner role."""
    try:
        project = await use_case.execute(
            project_id=project_id,
            requesting_user_id=current_user.user_id,
            **project_data.model_dump(exclude_unset=True),
        )
    except ProjectNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from None
    except InsufficientPermissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot modify projects",
        ) from None
    return ProjectResponse(
        project_id=project.project_id.value,
        name=project.name,
        key=project.key,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["projects"],
)
async def delete_project(
    project_id: str,
    current_user: UserModel = Depends(get_current_user),
    use_case: DeleteProjectUseCase = Depends(get_delete_project_use_case),
) -> None:
    """Delete project. Requires owner role."""
    try:
        await use_case.execute(project_id, current_user.user_id)
    except ProjectNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from None
    except InsufficientPermissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can delete it",
        ) from None


# ---- Member endpoints ----


@router.get(
    "/projects/{project_id}/members",
    response_model=ProjectMembersListResponse,
    tags=["projects"],
)
async def list_members(
    members: list[ProjectMemberModel] = Depends(resolve_project_members),
) -> ProjectMembersListResponse:
    """List all members of a project."""
    return ProjectMembersListResponse(members=list(members), total=len(members))


@router.post(
    "/projects/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["projects"],
)
async def add_member(
    project_id: str,
    member_data: ProjectMemberCreate,
    current_user: UserModel = Depends(get_current_user),
    use_case: AddProjectMemberUseCase = Depends(get_add_project_member_use_case),
) -> ProjectMemberResponse:
    """Add a member to the project. Requires owner role."""
    try:
        member = await use_case.execute(
            project_id=project_id,
            requesting_user_id=current_user.user_id,
            target_user_id=member_data.user_id,
            role=member_data.role,
        )
    except ProjectNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from None
    except InsufficientPermissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can add members",
        ) from None
    except UserAlreadyProjectMember:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this project",
        ) from None
    return ProjectMemberResponse(
        project_id=member.project_id.value,
        user_id=member.user_id.value,
        role=member.role,
        created_at=member.created_at,
    )


@router.patch(
    "/projects/{project_id}/members/{user_id}",
    response_model=ProjectMemberResponse,
    tags=["projects"],
)
async def update_member_role(
    project_id: str,
    user_id: str,
    member_data: ProjectMemberUpdate,
    current_user: UserModel = Depends(get_current_user),
    use_case: UpdateMemberRoleUseCase = Depends(get_update_member_role_use_case),
) -> ProjectMemberResponse:
    """Update a member's role. Requires owner role."""
    try:
        member = await use_case.execute(
            project_id=project_id,
            requesting_user_id=current_user.user_id,
            target_user_id=user_id,
            new_role=member_data.role,
        )
    except ProjectNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from None
    except InsufficientPermissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can change roles",
        ) from None
    except MemberNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        ) from None
    except LastOwnerCannotBeRemoved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote the last owner",
        ) from None
    return ProjectMemberResponse(
        project_id=member.project_id.value,
        user_id=member.user_id.value,
        role=member.role,
        created_at=member.created_at,
    )


@router.delete(
    "/projects/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["projects"],
)
async def remove_member(
    project_id: str,
    user_id: str,
    current_user: UserModel = Depends(get_current_user),
    use_case: RemoveProjectMemberUseCase = Depends(get_remove_project_member_use_case),
) -> None:
    """Remove a member from the project. Requires owner role."""
    try:
        await use_case.execute(project_id, current_user.user_id, user_id)
    except ProjectNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from None
    except InsufficientPermissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can remove members",
        ) from None
    except MemberNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        ) from None
    except LastOwnerCannotBeRemoved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the last owner",
        ) from None


# ---- Issue endpoints ----


@router.get("/issues", response_model=IssueListResponse, tags=["issues"])
async def list_issues(
    issues: list[IssueModel] = Depends(resolve_issue_list),
) -> IssueListResponse:
    """List all issues accessible to current user."""
    return IssueListResponse(issues=issues, total=len(issues))


@router.post(
    "/issues",
    response_model=IssueResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["issues"],
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


@router.get("/issues/{issue_id}", response_model=IssueResponse, tags=["issues"])
async def get_issue(
    issue: IssueModel = Depends(resolve_issue),
) -> IssueModel:
    """Get issue by ID."""
    return issue


@router.patch("/issues/{issue_id}", response_model=IssueResponse, tags=["issues"])
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
    "/issues/{issue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["issues"],
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
