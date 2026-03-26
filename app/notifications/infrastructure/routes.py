"""Notification API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.core.database import get_session
from app.identity.infrastructure.deps import get_current_user
from app.identity.infrastructure.jwt import verify_jwt_token
from app.identity.infrastructure.models import UserModel
from app.notifications.infrastructure import api_messages
from app.notifications.infrastructure.connection_manager import ConnectionManager
from app.notifications.infrastructure.deps import get_connection_manager
from app.notifications.infrastructure.models import NotificationModel
from app.notifications.infrastructure.schemas import (
    NotificationListResponse,
    NotificationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    is_read: bool | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> NotificationListResponse:
    """List notifications for the current user.

    Args:
        is_read: Optional filter by read status.
        session: Database session.
        current_user: The authenticated user.

    Returns:
        List of notifications.
    """
    query = select(NotificationModel).where(
        NotificationModel.user_id == current_user.user_id
    )
    if is_read is not None:
        query = query.where(NotificationModel.is_read == is_read)
    query = query.order_by(NotificationModel.created_at.desc())

    result = await session.execute(query)
    notifications = result.scalars().all()
    return NotificationListResponse(
        notifications=list(notifications), total=len(notifications)
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> NotificationModel:
    """Mark a notification as read.

    Args:
        notification_id: The notification UUID.
        session: Database session.
        current_user: The authenticated user.

    Returns:
        Updated notification.

    Raises:
        HTTPException: 404 if not found, 403 if not the owner.
    """
    result = await session.execute(
        select(NotificationModel).where(
            NotificationModel.notification_id == notification_id
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.NOTIFICATION_NOT_FOUND,
        )

    if notification.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=api_messages.NOTIFICATION_ACCESS_DENIED,
        )

    notification.is_read = True
    await session.commit()
    await session.refresh(notification)
    return notification


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
) -> None:
    """WebSocket endpoint for real-time notification push.

    Authenticates via JWT token in query parameter.

    Args:
        websocket: The WebSocket connection.
        token: JWT token for authentication.
        connection_manager: The ConnectionManager instance.
    """
    try:
        payload = verify_jwt_token(token)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = payload.sub
    await connection_manager.connect(user_id, websocket)
    logger.info("WebSocket connected: user=%s", user_id)

    try:
        while True:
            await websocket.receive_text()
    except Exception:
        connection_manager.disconnect(user_id)
        logger.info("WebSocket disconnected: user=%s", user_id)
