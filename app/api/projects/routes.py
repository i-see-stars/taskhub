"""Project API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.deps import get_current_user
from app.api.auth.models import User
from app.api.core.database import get_session
from app.api.projects.models import Project, ProjectMember, ProjectMemberRole
from app.api.projects.schemas import (
    ProjectCreate,
    ProjectListResponse,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectMembersListResponse,
    ProjectMemberUpdate,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["projects"])


async def _get_project_and_member(
    project_id: str,
    session: AsyncSession,
    current_user: User,
) -> tuple[Project, ProjectMember]:
    """Get project and verify user membership.

    Args:
        project_id: The project UUID.
        session: Database session.
        current_user: The authenticated user.

    Returns:
        Tuple of (Project, ProjectMember).

    Raises:
        HTTPException: 404 if project not found, 403 if user is not a member.
    """
    project_result = await session.execute(
        select(Project).where(Project.project_id == project_id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
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

    return project, member


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ProjectListResponse:
    """List all projects the current user is a member of."""
    result = await session.execute(
        select(Project)
        .join(ProjectMember)
        .where(ProjectMember.user_id == current_user.user_id)
    )
    projects = result.scalars().all()
    return ProjectListResponse(projects=list(projects), total=len(projects))


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Project:
    """Create a new project and add creator as owner."""
    existing = await session.execute(
        select(Project).where(Project.key == project_data.key)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project with this key already exists",
        )

    project = Project(**project_data.model_dump())
    session.add(project)
    await session.flush()  # get project_id before creating membership

    member = ProjectMember(
        project_id=project.project_id,
        user_id=current_user.user_id,
        role=ProjectMemberRole.OWNER,
    )
    session.add(member)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Project:
    """Get project by ID."""
    project, _ = await _get_project_and_member(project_id, session, current_user)
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Project:
    """Update project. Requires member or owner role."""
    project, member = await _get_project_and_member(project_id, session, current_user)

    if member.role == ProjectMemberRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot modify projects",
        )

    for field, value in project_data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    await session.commit()
    await session.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete project. Requires owner role."""
    project, member = await _get_project_and_member(project_id, session, current_user)

    if member.role != ProjectMemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can delete it",
        )

    await session.delete(project)
    await session.commit()


# --- Member management ---


@router.get("/{project_id}/members", response_model=ProjectMembersListResponse)
async def list_members(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ProjectMembersListResponse:
    """List all members of a project."""
    await _get_project_and_member(project_id, session, current_user)

    result = await session.execute(
        select(ProjectMember).where(ProjectMember.project_id == project_id)
    )
    members = result.scalars().all()
    return ProjectMembersListResponse(members=list(members), total=len(members))


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    project_id: str,
    member_data: ProjectMemberCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ProjectMember:
    """Add a member to the project. Requires owner role."""
    _, member = await _get_project_and_member(project_id, session, current_user)

    if member.role != ProjectMemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can add members",
        )

    # Check target user exists
    user_result = await session.execute(
        select(User).where(User.user_id == member_data.user_id)
    )
    if not user_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check not already a member
    existing = await session.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == member_data.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this project",
        )

    new_member = ProjectMember(
        project_id=project_id,
        user_id=member_data.user_id,
        role=member_data.role,
    )
    session.add(new_member)
    await session.commit()
    await session.refresh(new_member)
    return new_member


@router.patch(
    "/{project_id}/members/{user_id}",
    response_model=ProjectMemberResponse,
)
async def update_member_role(
    project_id: str,
    user_id: str,
    member_data: ProjectMemberUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ProjectMember:
    """Update a member's role. Requires owner role."""
    _, current_member = await _get_project_and_member(project_id, session, current_user)

    if current_member.role != ProjectMemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can change roles",
        )

    target_result = await session.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    target_member = target_result.scalar_one_or_none()
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Prevent demoting the last owner
    if (
        target_member.role == ProjectMemberRole.OWNER
        and member_data.role != ProjectMemberRole.OWNER
    ):
        owners_result = await session.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.role == ProjectMemberRole.OWNER,
            )
        )
        if len(owners_result.scalars().all()) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last owner",
            )

    target_member.role = member_data.role
    await session.commit()
    await session.refresh(target_member)
    return target_member


@router.delete(
    "/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    project_id: str,
    user_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove a member from the project. Requires owner role."""
    _, current_member = await _get_project_and_member(project_id, session, current_user)

    if current_member.role != ProjectMemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can remove members",
        )

    target_result = await session.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    target_member = target_result.scalar_one_or_none()
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Prevent removing the last owner
    if target_member.role == ProjectMemberRole.OWNER:
        owners_result = await session.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.role == ProjectMemberRole.OWNER,
            )
        )
        if len(owners_result.scalars().all()) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner",
            )

    await session.delete(target_member)
    await session.commit()
