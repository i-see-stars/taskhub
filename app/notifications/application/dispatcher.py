"""Notification dispatcher — application-layer abstractions and re-exports.

Abstract base classes (NotificationSender, NotificationService) and data carriers
(NotificationContext, NotificationResult) live here in the application layer.

Concrete implementations (InAppSender, EmailSender, etc.) live in the
infrastructure layer (senders.py) and are re-exported here for backward
compatibility.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

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


# Re-export concrete implementations from infrastructure for backward compatibility.
# This allows existing code to import from this module without changes.
from app.notifications.infrastructure.senders import (  # noqa: E402
    EmailNotificationService,
    EmailSender,
    InAppNotificationService,
    InAppSender,
    NotificationDispatcher,
)

__all__ = [
    "EmailNotificationService",
    "EmailSender",
    "InAppNotificationService",
    "InAppSender",
    "NotificationContext",
    "NotificationDispatcher",
    "NotificationResult",
    "NotificationSender",
    "NotificationService",
]
