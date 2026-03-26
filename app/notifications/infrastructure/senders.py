"""Concrete notification senders — infrastructure implementations.

These depend on SQLAlchemy and ConnectionManager (infrastructure concerns).
The abstract base classes live in the application layer (dispatcher.py).

Note: The import from dispatcher.py is safe despite the circular re-export
because dispatcher.py defines all abstract types before importing this module.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.application.dispatcher import (
    NotificationContext,
    NotificationResult,
    NotificationSender,
    NotificationService,
)
from app.notifications.infrastructure.connection_manager import ConnectionManager
from app.notifications.infrastructure.models import NotificationModel

logger = logging.getLogger(__name__)


class InAppSender(NotificationSender):
    """Concrete product — saves notification to DB and pushes via WebSocket."""

    def __init__(
        self, session: AsyncSession, connection_manager: ConnectionManager
    ) -> None:
        """Initialize with database session and connection manager.

        Args:
            session: The async database session.
            connection_manager: The WebSocket connection manager.
        """
        self.session = session
        self.connection_manager = connection_manager

    def channel_name(self) -> str:
        """Return channel name.

        Returns:
            The string 'in_app'.
        """
        return "in_app"

    async def send(self, context: NotificationContext) -> None:
        """Save notification to DB and push via WebSocket if user is online.

        Args:
            context: The notification data.
        """
        notification = NotificationModel(
            user_id=context.recipient_id,
            issue_id=context.issue_id,
            message=context.message,
        )
        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)

        created_at = (
            notification.created_at.isoformat()
            if notification.created_at is not None
            else None
        )
        await self.connection_manager.send(
            context.recipient_id,
            {
                "notification_id": notification.notification_id,
                "issue_id": context.issue_id,
                "message": context.message,
                "created_at": created_at,
            },
        )


class EmailSender(NotificationSender):
    """Concrete product — mock email sender (logs instead of sending)."""

    def channel_name(self) -> str:
        """Return channel name.

        Returns:
            The string 'email'.
        """
        return "email"

    async def send(self, context: NotificationContext) -> None:
        """Log email notification (mock implementation).

        Args:
            context: The notification data.
        """
        logger.info(
            "Email notification (mock): recipient=%s, message=%s",
            context.recipient_id,
            context.message,
        )


class InAppNotificationService(NotificationService):
    """Concrete creator — creates InAppSender."""

    def __init__(
        self, session: AsyncSession, connection_manager: ConnectionManager
    ) -> None:
        """Initialize with dependencies for InAppSender.

        Args:
            session: The async database session.
            connection_manager: The WebSocket connection manager.
        """
        self.session = session
        self.connection_manager = connection_manager

    def create_sender(self) -> NotificationSender:
        """Create an in-app notification sender.

        Returns:
            InAppSender with session and connection manager.
        """
        return InAppSender(
            session=self.session, connection_manager=self.connection_manager
        )


class EmailNotificationService(NotificationService):
    """Concrete creator — creates EmailSender."""

    def create_sender(self) -> NotificationSender:
        """Create a mock email notification sender.

        Returns:
            EmailSender instance.
        """
        return EmailSender()


class NotificationDispatcher:
    """Dispatches notifications to all enabled channels for a user."""

    def __init__(
        self, session: AsyncSession, connection_manager: ConnectionManager
    ) -> None:
        """Initialize with shared dependencies.

        Args:
            session: The async database session.
            connection_manager: The WebSocket connection manager.
        """
        self.session = session
        self.connection_manager = connection_manager

    async def dispatch(
        self,
        context: NotificationContext,
        notify_in_app: bool,
        notify_email: bool,
    ) -> list[NotificationResult]:
        """Send notification via all enabled channels.

        Args:
            context: The notification data.
            notify_in_app: Whether in-app channel is enabled.
            notify_email: Whether email channel is enabled.

        Returns:
            List of results, one per channel attempted.
        """
        services: list[NotificationService] = []
        if notify_in_app:
            services.append(
                InAppNotificationService(
                    session=self.session,
                    connection_manager=self.connection_manager,
                )
            )
        if notify_email:
            services.append(EmailNotificationService())

        results: list[NotificationResult] = []
        for service in services:
            result = await service.notify(context)
            results.append(result)
        return results
