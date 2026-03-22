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
from app.api.projects.models import Project


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


@pytest.mark.asyncio
async def test_assign_issue_creates_notification(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_project_with_member: Project,  # noqa: ARG001
    test_member_user: User,
    test_issue: Issue,
) -> None:
    """Test that assigning an issue creates a notification for the assignee."""
    # Assign the issue to member user
    response = await client.patch(
        f"/issues/{test_issue.issue_id}",
        headers=auth_headers,
        json={"assignee_id": test_member_user.user_id},
    )
    assert response.status_code == status.HTTP_200_OK

    # Check that a notification was created for the member
    member_response = await client.post(
        "/auth/access-token",
        data={
            "username": test_member_user.email,
            "password": "testpassword123",
        },
    )
    member_token = member_response.json()["access_token"]
    member_headers = {"Authorization": f"Bearer {member_token}"}

    notif_response = await client.get("/notifications", headers=member_headers)
    assert notif_response.status_code == status.HTTP_200_OK
    data = NotificationListResponse.model_validate(notif_response.json())
    assert data.total >= 1
    assert any(n.issue_id == test_issue.issue_id for n in data.notifications)


@pytest.mark.asyncio
async def test_assign_issue_no_notification_when_same_assignee(
    client: AsyncClient,
    auth_headers: dict[str, str],
    member_auth_headers: dict[str, str],
    test_project_with_member: Project,  # noqa: ARG001
    test_member_user: User,
    test_issue: Issue,
) -> None:
    """Test that re-assigning to the same user does not create duplicate notification."""
    # First assignment
    await client.patch(
        f"/issues/{test_issue.issue_id}",
        headers=auth_headers,
        json={"assignee_id": test_member_user.user_id},
    )

    # Get notification count
    notif_response = await client.get("/notifications", headers=member_auth_headers)
    count_after_first = NotificationListResponse.model_validate(
        notif_response.json()
    ).total

    # Same assignment again (no-op)
    await client.patch(
        f"/issues/{test_issue.issue_id}",
        headers=auth_headers,
        json={"assignee_id": test_member_user.user_id},
    )

    # Count should not increase
    notif_response = await client.get("/notifications", headers=member_auth_headers)
    count_after_second = NotificationListResponse.model_validate(
        notif_response.json()
    ).total
    assert count_after_second == count_after_first
