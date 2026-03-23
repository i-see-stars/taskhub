"""Notification dependencies."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import HTTPConnection

from app.api.core.database import get_session
from app.api.notifications.connection_manager import ConnectionManager
from app.api.notifications.services import NotificationDispatcher


def get_connection_manager(conn: HTTPConnection) -> ConnectionManager:
    """Get the ConnectionManager from app state.

    Works for both HTTP requests and WebSocket connections,
    since both inherit from HTTPConnection.

    Args:
        conn: The incoming HTTP or WebSocket connection.

    Returns:
        The ConnectionManager instance.
    """
    return conn.app.state.connection_manager  # type: ignore[no-any-return]


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
