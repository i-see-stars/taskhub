"""Issue tracking infrastructure ORM models.

Table names are UNCHANGED from app/api/ — no migration needed.
Cross-context SQLAlchemy relationships to User are REMOVED.
Only FK columns remain.
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.core.database import Base  # updated to app.core in Task 13
from app.issue_tracking.domain.value_objects import (
    IssueStatus,
    IssueType,
    Priority,
    ProjectRole,
)


class ProjectModel(Base):
    """ORM model for the project table."""

    __tablename__ = "project"  # MUST match existing table

    project_id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda _: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(sa.String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    key: Mapped[str] = mapped_column(
        sa.String(10), nullable=False, unique=True, index=True
    )

    issues: Mapped[list[IssueModel]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    members: Mapped[list[ProjectMemberModel]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectMemberModel(Base):
    """ORM model for the project_member table."""

    __tablename__ = "project_member"  # MUST match existing table

    project_id: Mapped[str] = mapped_column(
        sa.ForeignKey("project.project_id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("auth_user.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[ProjectRole] = mapped_column(
        sa.Enum(ProjectRole, name="projectmemberrole"),  # keep existing DB type name
        nullable=False,
    )

    project: Mapped[ProjectModel] = relationship(back_populates="members")
    # Cross-context relationship to User REMOVED — only FK column remains


class IssueModel(Base):
    """ORM model for the issue table."""

    __tablename__ = "issue"  # MUST match existing table

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
    priority: Mapped[Priority] = mapped_column(
        sa.Enum(Priority, name="issuepriority"),  # keep existing DB type name
        nullable=False,
        default=Priority.MEDIUM,
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

    project: Mapped[ProjectModel] = relationship(back_populates="issues")
    parent: Mapped[IssueModel | None] = relationship(
        "IssueModel", remote_side=[issue_id], back_populates="children"
    )
    children: Mapped[list[IssueModel]] = relationship(
        "IssueModel", back_populates="parent", cascade="all, delete-orphan"
    )
    comments: Mapped[list[CommentModel]] = relationship(
        back_populates="issue", cascade="all, delete-orphan"
    )
    # Cross-context relationships to User REMOVED (assignee, reporter)


class CommentModel(Base):
    """ORM model for the comment table."""

    __tablename__ = "comment"  # MUST match existing table

    comment_id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda _: str(uuid.uuid4())
    )
    issue_id: Mapped[str] = mapped_column(
        sa.ForeignKey("issue.issue_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[str] = mapped_column(
        sa.ForeignKey("auth_user.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    body: Mapped[str] = mapped_column(sa.Text, nullable=False)

    issue: Mapped[IssueModel] = relationship(back_populates="comments")
    # Cross-context relationship to User REMOVED
