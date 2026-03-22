"""Tests for notification endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.models import User
from app.api.issues.models import Issue
from app.api.notifications.models import Notification
from app.api.notifications.schemas import (
    NotificationListResponse,
    NotificationResponse,
)


@pytest.fixture
async def test_notification(
    db_session: AsyncSession, test_user: User, test_issue: Issue
) -> Notification:
    """Create a test notification."""
    notification = Notification(
        user_id=test_user.user_id,
        issue_id=test_issue.issue_id,
        message="You were assigned to: Test Issue",
    )
    db_session.add(notification)
    await db_session.commit()
    await db_session.refresh(notification)
    return notification


@pytest.mark.asyncio
async def test_list_notifications(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_notification: Notification,
) -> None:
    """Test listing notifications for current user."""
    response = await client.get("/notifications", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = NotificationListResponse.model_validate(response.json())
    assert data.total >= 1
    assert any(
        n.notification_id == test_notification.notification_id
        for n in data.notifications
    )


@pytest.mark.asyncio
async def test_list_notifications_filter_unread(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_notification: Notification,  # noqa: ARG001
) -> None:
    """Test listing only unread notifications."""
    response = await client.get("/notifications?is_read=false", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = NotificationListResponse.model_validate(response.json())
    assert all(not n.is_read for n in data.notifications)


@pytest.mark.asyncio
async def test_list_notifications_unauthorized(client: AsyncClient) -> None:
    """Test listing notifications without auth returns 401."""
    response = await client.get("/notifications")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_mark_notification_read(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_notification: Notification,
) -> None:
    """Test marking a notification as read."""
    response = await client.patch(
        f"/notifications/{test_notification.notification_id}/read",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = NotificationResponse.model_validate(response.json())
    assert data.is_read is True


@pytest.mark.asyncio
async def test_mark_notification_read_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Test marking nonexistent notification returns 404."""
    response = await client.patch(
        "/notifications/00000000-0000-0000-0000-000000000000/read",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_mark_notification_read_forbidden(
    client: AsyncClient,
    member_auth_headers: dict[str, str],
    test_notification: Notification,
) -> None:
    """Test that another user cannot mark someone else's notification as read."""
    response = await client.patch(
        f"/notifications/{test_notification.notification_id}/read",
        headers=member_auth_headers,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
