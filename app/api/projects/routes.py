"""Project API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.dependencies import get_current_user
from app.api.auth.models import User
from app.api.core.database import get_session
from app.api.projects.models import Project
from app.api.projects.schemas import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List all projects for current user."""
    result = await session.execute(
        select(Project).where(Project.owner_id == current_user.user_id)
    )
    projects = result.scalars().all()
    return ProjectListResponse(projects=projects, total=len(projects))


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new project."""
    # Check if project key already exists
    existing = await session.execute(
        select(Project).where(Project.key == project_data.key)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project with this key already exists",
        )

    project = Project(
        **project_data.model_dump(),
        owner_id=current_user.user_id,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get project by ID."""
    result = await session.execute(
        select(Project).where(
            Project.project_id == project_id,
            Project.owner_id == current_user.user_id,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update project."""
    result = await session.execute(
        select(Project).where(
            Project.project_id == project_id,
            Project.owner_id == current_user.user_id,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Update fields
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
):
    """Delete project."""
    result = await session.execute(
        select(Project).where(
            Project.project_id == project_id,
            Project.owner_id == current_user.user_id,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    await session.delete(project)
    await session.commit()
