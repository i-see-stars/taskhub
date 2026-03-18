"""Project database models."""

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.core.database import Base

if TYPE_CHECKING:
    from app.api.auth.models import User
    from app.api.issues.models import Issue


class ProjectMemberRole(StrEnum):
    """Project member role enumeration."""

    OWNER = "owner"
    MEMBER = "member"
    VIEWER = "viewer"


class Project(Base):
    """Project model - container for issues."""

    __tablename__ = "project"

    project_id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda _: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(sa.String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    key: Mapped[str] = mapped_column(
        sa.String(10), nullable=False, unique=True, index=True
    )

    # Relationships
    issues: Mapped[list[Issue]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    members: Mapped[list[ProjectMember]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectMember(Base):
    """Project member model - links users to projects with roles."""

    __tablename__ = "project_member"

    project_id: Mapped[str] = mapped_column(
        sa.ForeignKey("project.project_id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("auth_user.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[ProjectMemberRole] = mapped_column(
        sa.Enum(ProjectMemberRole), nullable=False
    )

    # Relationships
    project: Mapped[Project] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="project_memberships")
