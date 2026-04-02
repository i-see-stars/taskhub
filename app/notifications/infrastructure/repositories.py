"""PostgreSQL implementation of notification repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.domain.entities import Notification
from app.notifications.domain.exceptions import NotificationNotFound
from app.notifications.domain.repositories import NotificationRepository
from app.notifications.infrastructure.models import NotificationModel
from app.shared.domain.identifiers import NotificationId, UserId


class PostgresNotificationRepository(NotificationRepository):
    """Notification repository backed by PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session.

        Args:
            session: The async database session.
        """
        self._session = session

    def _to_domain(self, model: NotificationModel) -> Notification:
        """Map ORM model to domain entity.

        Args:
            model: The ORM notification model.

        Returns:
            Domain Notification entity.
        """
        return Notification(
            notification_id=NotificationId(model.notification_id),
            user_id=UserId(model.user_id),
            issue_id=model.issue_id,
            message=model.message,
            is_read=model.is_read,
            created_at=model.created_at,
        )

    async def get_by_id(self, notification_id: NotificationId) -> Notification:
        """Fetch notification by ID.

        Raises:
            NotificationNotFound: If not found.
        """
        result = await self._session.execute(
            select(NotificationModel).where(
                NotificationModel.notification_id == notification_id.value
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise NotificationNotFound(
                f"Notification {notification_id.value!r} not found"
            )
        return self._to_domain(model)

    async def save(self, notification: Notification) -> Notification:
        """Persist a new or updated notification."""
        result = await self._session.execute(
            select(NotificationModel).where(
                NotificationModel.notification_id == notification.notification_id.value
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            model = NotificationModel(
                notification_id=notification.notification_id.value,
                user_id=notification.user_id.value,
                issue_id=notification.issue_id,
                message=notification.message,
                is_read=notification.is_read,
            )
            self._session.add(model)
        else:
            model.is_read = notification.is_read
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_domain(model)
