"""Notification dependencies."""

from __future__ import annotations

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import HTTPConnection

from app.core.database import get_session
from app.identity.infrastructure.deps import get_current_user
from app.identity.infrastructure.models import UserModel
from app.notifications.application.dispatcher import NotificationDispatcher
from app.notifications.application.use_cases import MarkNotificationReadUseCase
from app.notifications.infrastructure.connection_manager import ConnectionManager
from app.notifications.infrastructure.models import NotificationModel
from app.notifications.infrastructure.queries import list_notifications_for_user
from app.notifications.infrastructure.repositories import (
    PostgresNotificationRepository,
)
from app.shared.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


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


def get_mark_notification_read_use_case(
    session: AsyncSession = Depends(get_session),
) -> MarkNotificationReadUseCase:
    """Create MarkNotificationReadUseCase with injected dependencies.

    Args:
        session: Database session.

    Returns:
        Configured use case.
    """
    return MarkNotificationReadUseCase(
        notification_repo=PostgresNotificationRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


async def resolve_notification_list(
    is_read: bool | None = Query(None),
    category: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[NotificationModel]:
    """Resolve notification list for current user.

    Args:
        is_read: Optional filter by read status.
        category: Optional JSONB payload category filter.
        session: Database session.
        current_user: The authenticated user.

    Returns:
        List of notification models.
    """
    return await list_notifications_for_user(
        session,
        current_user.user_id,
        is_read=is_read,
        category=category,
    )
