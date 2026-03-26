"""Tests for the in-process event bus."""

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from app.core.event_bus import EventBus
from app.shared.domain.events import DomainEvent


@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    """Test domain event for order placement."""

    order_id: str


@dataclass(frozen=True)
class OrderCancelled(DomainEvent):
    """Test domain event for order cancellation."""

    order_id: str


@pytest.mark.asyncio
async def test_event_bus_dispatches_to_handler() -> None:
    """Test that event bus dispatches events to subscribed handlers."""
    received: list[DomainEvent] = []

    async def handler(event: DomainEvent) -> None:
        received.append(event)

    bus = EventBus()
    bus.subscribe(OrderPlaced, handler)

    event = OrderPlaced(order_id="123", occurred_at=datetime.now(UTC))
    await bus.publish(event)

    assert len(received) == 1
    assert received[0] is event


@pytest.mark.asyncio
async def test_event_bus_only_dispatches_matching_type() -> None:
    """Test that event bus only dispatches events of matching type."""
    received: list[DomainEvent] = []

    async def handler(event: DomainEvent) -> None:
        received.append(event)

    bus = EventBus()
    bus.subscribe(OrderPlaced, handler)

    await bus.publish(OrderCancelled(order_id="x", occurred_at=datetime.now(UTC)))
    assert len(received) == 0


@pytest.mark.asyncio
async def test_event_bus_multiple_handlers_for_same_event() -> None:
    """Test that event bus supports multiple handlers for same event type."""
    results: list[str] = []

    async def handler_a(_event: DomainEvent) -> None:
        results.append("a")

    async def handler_b(_event: DomainEvent) -> None:
        results.append("b")

    bus = EventBus()
    bus.subscribe(OrderPlaced, handler_a)
    bus.subscribe(OrderPlaced, handler_b)

    await bus.publish(OrderPlaced(order_id="1", occurred_at=datetime.now(UTC)))
    assert results == ["a", "b"]


@pytest.mark.asyncio
async def test_empty_event_bus_is_safe() -> None:
    """Test that publishing to empty bus does not raise."""
    bus = EventBus()
    # No subscriptions — should not raise
    await bus.publish(OrderPlaced(order_id="x", occurred_at=datetime.now(UTC)))


@pytest.mark.asyncio
async def test_event_bus_swallows_handler_exceptions() -> None:
    """Handler exceptions must not propagate out of publish()."""

    async def failing_handler(_event: DomainEvent) -> None:
        raise RuntimeError("handler failed")

    bus = EventBus()
    bus.subscribe(OrderPlaced, failing_handler)

    # Must not raise
    await bus.publish(OrderPlaced(order_id="x", occurred_at=datetime.now(UTC)))


@pytest.mark.asyncio
async def test_event_bus_continues_after_handler_failure() -> None:
    """Subsequent handlers must run even when an earlier handler raises."""
    results: list[str] = []

    async def failing_handler(_event: DomainEvent) -> None:
        raise RuntimeError("boom")

    async def succeeding_handler(_event: DomainEvent) -> None:
        results.append("ok")

    bus = EventBus()
    bus.subscribe(OrderPlaced, failing_handler)
    bus.subscribe(OrderPlaced, succeeding_handler)

    await bus.publish(OrderPlaced(order_id="x", occurred_at=datetime.now(UTC)))
    assert results == ["ok"]
