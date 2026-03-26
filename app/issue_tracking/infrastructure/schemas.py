"""Issue tracking Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.issue_tracking.domain.value_objects import (
    IssueStatus,
    IssueType,
    Priority,
    ProjectRole,
)

# --- Project schemas ---


class ProjectBase(BaseModel):
    """Base project schema."""

    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    key: str = Field(..., min_length=2, max_length=10, pattern=r"^[A-Z][A-Z0-9]*$")


class ProjectCreate(ProjectBase):
    """Project creation schema."""


class ProjectUpdate(BaseModel):
    """Project update schema - all fields optional."""

    name: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = None


class ProjectResponse(ProjectBase):
    """Project response schema."""

    project_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """Project list response schema."""

    projects: list[ProjectResponse]
    total: int


class ProjectMemberCreate(BaseModel):
    """Schema for adding a member to a project."""

    user_id: str
    role: ProjectRole = ProjectRole.MEMBER


class ProjectMemberUpdate(BaseModel):
    """Schema for updating a member's role."""

    role: ProjectRole


class ProjectMemberResponse(BaseModel):
    """Project member response schema."""

    project_id: str
    user_id: str
    role: ProjectRole
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectMembersListResponse(BaseModel):
    """Project members list response schema."""

    members: list[ProjectMemberResponse]
    total: int


# --- Issue schemas ---


class IssueBase(BaseModel):
    """Base issue schema."""

    title: str = Field(..., min_length=1, max_length=512)
    description: str | None = None
    type: IssueType
    status: IssueStatus = IssueStatus.TODO
    priority: Priority = Priority.MEDIUM
    parent_id: str | None = None
    assignee_id: str | None = None


class IssueCreate(IssueBase):
    """Issue creation schema."""

    project_id: str


class IssueUpdate(BaseModel):
    """Issue update schema - all fields optional."""

    title: str | None = Field(None, min_length=1, max_length=512)
    description: str | None = None
    type: IssueType | None = None
    status: IssueStatus | None = None
    priority: Priority | None = None
    parent_id: str | None = None
    assignee_id: str | None = None


class IssueResponse(IssueBase):
    """Issue response schema."""

    issue_id: str
    project_id: str
    reporter_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IssueListResponse(BaseModel):
    """Issue list response schema."""

    issues: list[IssueResponse]
    total: int


# --- Comment schemas ---


class CommentCreate(BaseModel):
    """Comment creation schema."""

    body: str = Field(..., min_length=1)


class CommentResponse(BaseModel):
    """Comment response schema."""

    comment_id: str
    issue_id: str
    author_id: str
    body: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CommentListResponse(BaseModel):
    """Comment list response schema."""

    comments: list[CommentResponse]
    total: int
