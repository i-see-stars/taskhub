"""Base domain event."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events.

    All domain events are immutable value objects with a timestamp.
    Subclasses add event-specific fields.
    """

    occurred_at: datetime
