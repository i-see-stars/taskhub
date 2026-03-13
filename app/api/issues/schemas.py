"""Issue Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.api.issues.models import IssuePriority, IssueStatus, IssueType


class IssueBase(BaseModel):
    """Base issue schema."""

    title: str = Field(..., min_length=1, max_length=512)
    description: str | None = None
    type: IssueType
    status: IssueStatus = IssueStatus.TODO
    priority: IssuePriority = IssuePriority.MEDIUM
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
    priority: IssuePriority | None = None
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
