"""In-process synchronous event bus for domain event dispatch."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

from app.shared.domain.events import DomainEvent

logger = logging.getLogger(__name__)

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    """Request-scoped synchronous event bus.

    Handlers are subscribed at request time. All handlers for a given event
    type are called in subscription order when that event is published.
    Exceptions in handlers are logged and swallowed to prevent domain
    operations from failing due to side-effect failures.
    """

    def __init__(self) -> None:
        """Initialize with empty handler registry."""
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """Register a handler for an event type.

        Args:
            event_type: The domain event class to subscribe to.
            handler: Async callable that receives the event.
        """
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        """Dispatch event to all registered handlers.

        Args:
            event: The domain event to dispatch.
        """
        handlers = self._handlers.get(type(event), [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "Event handler %s failed for event %s",
                    handler.__name__,
                    type(event).__name__,
                )
