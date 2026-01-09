from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_session
from api.projects.models import Project
from api.projects.schemas import ProjectCreate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post(
    "", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED
)
async def create_project(
    payload: ProjectCreate, session: AsyncSession = Depends(get_session)
):
    exists = await session.scalar(
        select(Project).where(Project.name == payload.name)
    )
    if exists:
        raise HTTPException(
            status_code=409, detail="Project with this name already exists"
        )

    project = Project(name=payload.name)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return ProjectResponse.model_validate(project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Project).order_by(Project.id))
    projects = result.scalars().all()
    return [ProjectResponse.model_validate(p) for p in projects]
