"""Project and project-member API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.identity.infrastructure.deps import get_current_user
from app.identity.infrastructure.models import UserModel
from app.issue_tracking.application.project_use_cases import (
    AddProjectMemberUseCase,
    CreateProjectUseCase,
    DeleteProjectUseCase,
    RemoveProjectMemberUseCase,
    UpdateMemberRoleUseCase,
    UpdateProjectUseCase,
)
from app.issue_tracking.domain.exceptions import (
    DuplicateProjectKey,
    InsufficientPermissions,
    LastOwnerCannotBeRemoved,
    MemberNotFound,
    ProjectNotFound,
    UserAlreadyProjectMember,
)
from app.issue_tracking.infrastructure.deps import (
    get_add_project_member_use_case,
    get_create_project_use_case,
    get_delete_project_use_case,
    get_remove_project_member_use_case,
    get_update_member_role_use_case,
    get_update_project_use_case,
    resolve_project,
    resolve_project_list,
    resolve_project_members,
)
from app.issue_tracking.infrastructure.models import ProjectMemberModel, ProjectModel
from app.issue_tracking.infrastructure.schemas import (
    ProjectCreate,
    ProjectListResponse,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectMembersListResponse,
    ProjectMemberUpdate,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter(tags=["projects"])


@router.get(
    "",
    response_model=ProjectListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_projects(
    projects: list[ProjectModel] = Depends(resolve_project_list),
) -> ProjectListResponse:
    """List all projects the current user is a member of."""
    return ProjectListResponse(projects=projects, total=len(projects))


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
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


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
)
async def get_project(
    project: ProjectModel = Depends(resolve_project),
) -> ProjectModel:
    """Get project by ID."""
    return project


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
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
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
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
    "/{project_id}/members",
    response_model=ProjectMembersListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_members(
    members: list[ProjectMemberModel] = Depends(resolve_project_members),
) -> ProjectMembersListResponse:
    """List all members of a project."""
    return ProjectMembersListResponse(members=list(members), total=len(members))


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
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
    "/{project_id}/members/{user_id}",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_200_OK,
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
    "/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
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
