"""Project database models."""

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.core.database import Base

if TYPE_CHECKING:
    from app.api.issues.models import Issue


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
    owner_id: Mapped[str] = mapped_column(
        sa.ForeignKey("auth_user.user_id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    issues: Mapped[list[Issue]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
