"""Notification API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status

from app.identity.infrastructure.deps import get_current_user
from app.identity.infrastructure.jwt import verify_jwt_token
from app.identity.infrastructure.models import UserModel
from app.notifications.application.use_cases import MarkNotificationReadUseCase
from app.notifications.domain.exceptions import (
    NotificationAccessDenied,
    NotificationNotFound,
)
from app.notifications.infrastructure import api_messages
from app.notifications.infrastructure.connection_manager import ConnectionManager
from app.notifications.infrastructure.deps import (
    get_connection_manager,
    get_mark_notification_read_use_case,
    resolve_notification_list,
)
from app.notifications.infrastructure.models import NotificationModel
from app.notifications.infrastructure.schemas import (
    NotificationListResponse,
    NotificationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notifications"])


@router.get("", response_model=NotificationListResponse, status_code=status.HTTP_200_OK)
async def list_notifications(
    notifications: list[NotificationModel] = Depends(resolve_notification_list),
) -> NotificationListResponse:
    """List notifications for the current user."""
    return NotificationListResponse(
        notifications=list(notifications), total=len(notifications)
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
)
async def mark_notification_read(
    notification_id: str,
    current_user: UserModel = Depends(get_current_user),
    use_case: MarkNotificationReadUseCase = Depends(
        get_mark_notification_read_use_case
    ),
) -> NotificationResponse:
    """Mark a notification as read."""
    try:
        notification = await use_case.execute(notification_id, current_user.user_id)
    except NotificationNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.NOTIFICATION_NOT_FOUND,
        ) from None
    except NotificationAccessDenied:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=api_messages.NOTIFICATION_ACCESS_DENIED,
        ) from None
    return NotificationResponse(
        notification_id=notification.notification_id.value,
        issue_id=notification.issue_id,
        message=notification.message,
        payload=notification.payload,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )


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
