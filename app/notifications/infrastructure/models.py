"""Notification infrastructure ORM models.

Table name UNCHANGED — no migration needed.
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NotificationModel(Base):
    """ORM model for the notification table."""

    __tablename__ = "notification"  # MUST match existing table

    notification_id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda _: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        sa.ForeignKey("auth_user.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issue_id: Mapped[str] = mapped_column(
        sa.ForeignKey("issue.issue_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message: Mapped[str] = mapped_column(sa.Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
