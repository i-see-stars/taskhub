"""Comment Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


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
