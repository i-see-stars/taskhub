"""Notification application use cases."""

from __future__ import annotations

from app.notifications.domain.entities import Notification
from app.notifications.domain.exceptions import NotificationAccessDenied
from app.notifications.domain.repositories import NotificationRepository
from app.shared.domain.identifiers import NotificationId, UserId
from app.shared.domain.unit_of_work import UnitOfWork


class MarkNotificationReadUseCase:
    """Mark a notification as read."""

    def __init__(
        self,
        notification_repo: NotificationRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        """Initialize with repository and unit of work.

        Args:
            notification_repo: Notification repository.
            unit_of_work: Unit of work for transaction management.
        """
        self._repo = notification_repo
        self._unit_of_work = unit_of_work

    async def execute(
        self, notification_id: str, requesting_user_id: str
    ) -> Notification:
        """Mark notification as read.

        Args:
            notification_id: The notification UUID.
            requesting_user_id: The user performing the action.

        Returns:
            The updated Notification entity.

        Raises:
            NotificationNotFound: If notification doesn't exist.
            NotificationAccessDenied: If user doesn't own this notification.
        """
        notification = await self._repo.get_by_id(NotificationId(notification_id))
        if notification.user_id != UserId(requesting_user_id):
            raise NotificationAccessDenied("Cannot access another user's notification")
        notification.is_read = True
        saved = await self._repo.save(notification)
        await self._unit_of_work.commit()
        return saved
