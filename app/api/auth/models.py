"""Auth database models."""

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.core.database import Base

if TYPE_CHECKING:
    from app.api.projects.models import ProjectMember


class User(Base):
    """User database model."""

    __tablename__ = "auth_user"

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

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")  # noqa: UP037
    project_memberships: Mapped[list[ProjectMember]] = relationship(
        back_populates="user"
    )  # noqa: UP037


class RefreshToken(Base):
    """Refresh token database model."""

    __tablename__ = "auth_refresh_token"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    refresh_token: Mapped[str] = mapped_column(
        sa.String(512), nullable=False, unique=True, index=True
    )
    used: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    exp: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)

    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("auth_user.user_id", ondelete="CASCADE"),
    )
    user: Mapped[User] = relationship(back_populates="refresh_tokens")
