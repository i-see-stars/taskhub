"""Notification domain entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.shared.domain.base import Entity
from app.shared.domain.identifiers import NotificationId, UserId


@dataclass(eq=False)
class Notification(Entity):
    """An in-app notification addressed to a user."""

    notification_id: NotificationId
    user_id: UserId
    issue_id: str
    message: str
    is_read: bool
    created_at: datetime | None = None
