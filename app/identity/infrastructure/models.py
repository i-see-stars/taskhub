"""Identity infrastructure ORM models.

These map to the same database tables as app/api/auth/models.py.
Table names are UNCHANGED — no migration needed.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.core.database import Base  # updated to app.core.database in Task 13

if TYPE_CHECKING:
    pass  # cross-context relationships removed


class UserModel(Base):
    """ORM model for the auth_user table."""

    __tablename__ = "auth_user"  # MUST match existing table — no migration

    user_id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda _: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(
        sa.String(256), nullable=False, unique=True, index=True
    )
    hashed_password: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    notify_in_app: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    notify_email: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )

    refresh_tokens: Mapped[list[RefreshTokenModel]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    # Cross-context relationship removed: project_memberships


class RefreshTokenModel(Base):
    """ORM model for the auth_refresh_token table."""

    __tablename__ = "auth_refresh_token"  # MUST match existing table

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    refresh_token: Mapped[str] = mapped_column(
        sa.String(512), nullable=False, unique=True, index=True
    )
    used: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    exp: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("auth_user.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user: Mapped[UserModel] = relationship(back_populates="refresh_tokens")
