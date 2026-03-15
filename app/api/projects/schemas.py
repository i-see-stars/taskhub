"""Project Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    """Base project schema."""

    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    key: str = Field(..., min_length=2, max_length=10, pattern=r"^[A-Z][A-Z0-9]*$")


class ProjectCreate(ProjectBase):
    """Project creation schema."""

    pass


class ProjectUpdate(BaseModel):
    """Project update schema - all fields optional."""

    name: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = None


class ProjectResponse(ProjectBase):
    """Project response schema."""

    project_id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """Project list response schema."""

    projects: list[ProjectResponse]
    total: int
