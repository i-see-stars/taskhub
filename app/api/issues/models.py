"""Issue database models."""

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.core.database import Base

if TYPE_CHECKING:
    from app.api.projects.models import Project


class IssueType(StrEnum):
    """Issue type enumeration."""

    EPIC = "epic"
    STORY = "story"
    TASK = "task"
    BUG = "bug"


class IssueStatus(StrEnum):
    """Issue status enumeration."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class IssuePriority(StrEnum):
    """Issue priority enumeration."""

    LOWEST = "lowest"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    HIGHEST = "highest"


class Issue(Base):
    """Issue model - universal task (epic/story/task/bug)."""

    __tablename__ = "issue"

    issue_id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda _: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        sa.ForeignKey("project.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[str | None] = mapped_column(
        sa.ForeignKey("issue.issue_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    type: Mapped[IssueType] = mapped_column(
        sa.Enum(IssueType), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[IssueStatus] = mapped_column(
        sa.Enum(IssueStatus), nullable=False, default=IssueStatus.TODO, index=True
    )
    priority: Mapped[IssuePriority] = mapped_column(
        sa.Enum(IssuePriority), nullable=False, default=IssuePriority.MEDIUM
    )
    assignee_id: Mapped[str | None] = mapped_column(
        sa.ForeignKey("auth_user.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reporter_id: Mapped[str] = mapped_column(
        sa.ForeignKey("auth_user.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    project: Mapped[Project] = relationship(back_populates="issues")
    parent: Mapped[Issue | None] = relationship(
        "Issue", remote_side=[issue_id], back_populates="children"
    )
    children: Mapped[list[Issue]] = relationship(
        "Issue", back_populates="parent", cascade="all, delete-orphan"
    )
