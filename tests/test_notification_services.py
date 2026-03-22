"""Tests for notification services (Factory Method pattern)."""

from unittest.mock import AsyncMock

import pytest

from app.api.notifications.services import (
    EmailNotificationService,
    EmailSender,
    InAppNotificationService,
    InAppSender,
    NotificationContext,
    NotificationDispatcher,
    NotificationSender,
    NotificationService,
)


class FakeSender(NotificationSender):
    """Fake sender for testing the Factory Method pattern."""

    def __init__(self) -> None:
        """Initialize with empty sent list."""
        self.sent: list[NotificationContext] = []

    def channel_name(self) -> str:
        """Return fake channel name."""
        return "fake"

    async def send(self, context: NotificationContext) -> None:
        """Record the context instead of sending."""
        self.sent.append(context)


class FakeNotificationService(NotificationService):
    """Fake creator for testing base class logic."""

    def __init__(self) -> None:
        """Initialize with a shared FakeSender."""
        self.fake_sender = FakeSender()

    def create_sender(self) -> NotificationSender:
        """Return the fake sender."""
        return self.fake_sender


@pytest.mark.asyncio
async def test_notify_calls_sender_and_returns_result() -> None:
    """Test that base notify() calls create_sender().send() and returns result."""
    service = FakeNotificationService()
    context = NotificationContext(
        recipient_id="user-1", issue_id="issue-1", message="Test message"
    )

    result = await service.notify(context)

    assert result.success is True
    assert result.channel == "fake"
    assert result.recipient_id == "user-1"
    assert result.message == "Test message"
    assert len(service.fake_sender.sent) == 1
    assert service.fake_sender.sent[0] is context


@pytest.mark.asyncio
async def test_notify_handles_sender_exception() -> None:
    """Test that notify() catches sender exceptions and returns failure."""
    service = FakeNotificationService()
    service.fake_sender.send = AsyncMock(side_effect=RuntimeError("boom"))  # type: ignore[method-assign]
    context = NotificationContext(
        recipient_id="user-1", issue_id="issue-1", message="Test"
    )

    result = await service.notify(context)

    assert result.success is False
    assert result.channel == "fake"


@pytest.mark.asyncio
async def test_email_service_creates_email_sender() -> None:
    """Test that EmailNotificationService.create_sender() returns EmailSender."""
    service = EmailNotificationService()
    sender = service.create_sender()
    assert isinstance(sender, EmailSender)
    assert sender.channel_name() == "email"


@pytest.mark.asyncio
async def test_email_sender_does_not_raise() -> None:
    """Test that mock EmailSender.send() completes without error."""
    sender = EmailSender()
    context = NotificationContext(
        recipient_id="user-1", issue_id="issue-1", message="Hello"
    )
    await sender.send(context)  # should not raise


@pytest.mark.asyncio
async def test_inapp_service_creates_inapp_sender() -> None:
    """Test that InAppNotificationService.create_sender() returns InAppSender."""
    session = AsyncMock()
    manager = AsyncMock()
    service = InAppNotificationService(session=session, connection_manager=manager)
    sender = service.create_sender()
    assert isinstance(sender, InAppSender)
    assert sender.channel_name() == "in_app"


# === Dispatcher tests ===


@pytest.mark.asyncio
async def test_dispatcher_sends_to_all_enabled_channels() -> None:
    """Test that dispatcher calls both in-app and email when both enabled."""
    session = AsyncMock()
    # Make flush and refresh no-ops, but allow attribute access on added objects
    session.add = lambda _: None
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    manager = AsyncMock()
    manager.send = AsyncMock()
    dispatcher = NotificationDispatcher(session=session, connection_manager=manager)
    context = NotificationContext(
        recipient_id="user-1", issue_id="issue-1", message="Assigned"
    )

    results = await dispatcher.dispatch(context, notify_in_app=True, notify_email=True)

    assert len(results) == 2
    channels = {r.channel for r in results}
    assert channels == {"in_app", "email"}
    assert all(r.success for r in results)


@pytest.mark.asyncio
async def test_dispatcher_skips_disabled_channels() -> None:
    """Test that dispatcher skips channels that are disabled."""
    session = AsyncMock()
    manager = AsyncMock()
    dispatcher = NotificationDispatcher(session=session, connection_manager=manager)
    context = NotificationContext(
        recipient_id="user-1", issue_id="issue-1", message="Assigned"
    )

    results = await dispatcher.dispatch(context, notify_in_app=False, notify_email=True)

    assert len(results) == 1
    assert results[0].channel == "email"


@pytest.mark.asyncio
async def test_dispatcher_no_channels_enabled() -> None:
    """Test that dispatcher returns empty list when no channels enabled."""
    session = AsyncMock()
    manager = AsyncMock()
    dispatcher = NotificationDispatcher(session=session, connection_manager=manager)
    context = NotificationContext(
        recipient_id="user-1", issue_id="issue-1", message="Assigned"
    )

    results = await dispatcher.dispatch(
        context, notify_in_app=False, notify_email=False
    )

    assert results == []
