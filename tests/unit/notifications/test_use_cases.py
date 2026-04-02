"""Unit tests for notification use cases."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.notifications.application.use_cases import MarkNotificationReadUseCase
from app.notifications.domain.entities import Notification
from app.notifications.domain.exceptions import NotificationAccessDenied
from app.shared.domain.identifiers import NotificationId, UserId


def _make_notification(
    owner_id: str = "user-1",
    is_read: bool = False,
) -> Notification:
    """Create a test notification."""
    return Notification(
        notification_id=NotificationId("notif-1"),
        user_id=UserId(owner_id),
        issue_id="issue-1",
        message="Test notification",
        is_read=is_read,
        created_at=datetime.now(),
    )


@pytest.mark.asyncio
async def test_mark_notification_read_success() -> None:
    """Test marking a notification as read."""
    notification = _make_notification(owner_id="user-1")
    repo = AsyncMock()
    repo.get_by_id.return_value = notification
    repo.save.side_effect = lambda n: n
    unit_of_work = AsyncMock()

    use_case = MarkNotificationReadUseCase(
        notification_repo=repo, unit_of_work=unit_of_work
    )
    result = await use_case.execute("notif-1", "user-1")

    repo.save.assert_called_once()
    saved = repo.save.call_args[0][0]
    assert saved.is_read is True
    unit_of_work.commit.assert_called_once()
    assert result.is_read is True


@pytest.mark.asyncio
async def test_mark_notification_read_wrong_user() -> None:
    """Test that marking another user's notification raises."""
    notification = _make_notification(owner_id="user-1")
    repo = AsyncMock()
    repo.get_by_id.return_value = notification
    unit_of_work = AsyncMock()

    use_case = MarkNotificationReadUseCase(
        notification_repo=repo, unit_of_work=unit_of_work
    )
    with pytest.raises(NotificationAccessDenied):
        await use_case.execute("notif-1", "stranger")
