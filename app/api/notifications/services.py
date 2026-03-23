"""Notification services with Factory Method pattern."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.notifications.connection_manager import ConnectionManager
from app.api.notifications.models import Notification

logger = logging.getLogger(__name__)


@dataclass
class NotificationContext:
    """Data carrier for notification information."""

    recipient_id: str
    issue_id: str
    message: str


@dataclass
class NotificationResult:
    """Result of a notification delivery attempt."""

    channel: str
    recipient_id: str
    message: str
    success: bool


# === Product hierarchy ===


class NotificationSender(ABC):
    """Abstract product — sends a notification via a specific channel."""

    @abstractmethod
    async def send(self, context: NotificationContext) -> None:
        """Send a notification.

        Args:
            context: The notification data.
        """

    @abstractmethod
    def channel_name(self) -> str:
        """Return the name of this notification channel.

        Returns:
            Channel name string.
        """


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
        notification = Notification(
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


# === Creator hierarchy ===


class NotificationService(ABC):
    """Abstract creator — contains shared notification delivery logic."""

    @abstractmethod
    def create_sender(self) -> NotificationSender:
        """Factory method — create a channel-specific sender.

        Returns:
            A NotificationSender instance.
        """

    async def notify(self, context: NotificationContext) -> NotificationResult:
        """Send a notification using the factory method.

        Creates a sender via create_sender(), delegates sending to it,
        and returns the result. Catches exceptions from the sender.

        Args:
            context: The notification data.

        Returns:
            NotificationResult with success/failure status.
        """
        sender = self.create_sender()
        try:
            await sender.send(context)
            success = True
        except Exception:
            logger.exception(
                "Notification failed via %s for user %s",
                sender.channel_name(),
                context.recipient_id,
            )
            success = False
        return NotificationResult(
            channel=sender.channel_name(),
            recipient_id=context.recipient_id,
            message=context.message,
            success=success,
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


# === Dispatcher ===


class NotificationDispatcher:
    """Dispatches notifications to all enabled channels for a user.

    Checks user preferences and instantiates the appropriate Creator
    for each enabled channel.
    """

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
