"""Notification domain repository interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.notifications.domain.entities import Notification
from app.shared.domain.identifiers import NotificationId


class NotificationRepository(ABC):
    """Abstract repository for Notification entity."""

    @abstractmethod
    async def get_by_id(self, notification_id: NotificationId) -> Notification:
        """Fetch notification by ID.

        Raises:
            NotificationNotFound: If not found.
        """

    @abstractmethod
    async def save(self, notification: Notification) -> Notification:
        """Persist a new or updated notification."""
