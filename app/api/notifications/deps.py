"""Notification dependencies."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.core.database import get_session
from app.api.notifications.connection_manager import ConnectionManager
from app.api.notifications.services import NotificationDispatcher


def get_connection_manager(request: Request) -> ConnectionManager:
    """Get the ConnectionManager from app state.

    Args:
        request: The incoming request.

    Returns:
        The ConnectionManager instance.
    """
    return request.app.state.connection_manager  # type: ignore[no-any-return]


def get_notification_dispatcher(
    session: AsyncSession = Depends(get_session),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
) -> NotificationDispatcher:
    """Get a NotificationDispatcher with injected dependencies.

    Args:
        session: The async database session.
        connection_manager: The WebSocket connection manager.

    Returns:
        A configured NotificationDispatcher.
    """
    return NotificationDispatcher(
        session=session, connection_manager=connection_manager
    )
