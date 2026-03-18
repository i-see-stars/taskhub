"""Comment database models."""

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.core.database import Base

if TYPE_CHECKING:
    from app.api.auth.models import User
    from app.api.issues.models import Issue


class Comment(Base):
    """Comment model - user comment on an issue."""

    __tablename__ = "comment"

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

    # Relationships
    issue: Mapped[Issue] = relationship(back_populates="comments")
    author: Mapped[User] = relationship()
