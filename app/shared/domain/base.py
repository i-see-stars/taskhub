"""Shared kernel base classes for DDD building blocks."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from app.shared.domain.events import DomainEvent


@dataclass(eq=False)
class Entity:
    """Base class for domain entities. Equality is based on identity, not value."""

    def __eq__(self, other: object) -> bool:
        """Compare by the first dataclass field (the id field).

        Args:
            other: The object to compare.

        Returns:
            True if both entities have the same identity.
        """
        if not isinstance(other, self.__class__):
            return False
        fields = dataclasses.fields(self)
        if not fields:
            return False
        id_field = fields[0].name
        return bool(getattr(self, id_field) == getattr(other, id_field))

    def __hash__(self) -> int:
        """Hash by identity field.

        Returns:
            Hash of the identity field value.
        """
        fields = dataclasses.fields(self)
        if not fields:
            return hash(id(self))
        id_field = fields[0].name
        return hash(getattr(self, id_field))


@dataclass(eq=False)
class AggregateRoot(Entity):
    """Base class for aggregate roots. Collects domain events for publication."""

    def __post_init__(self) -> None:
        """Initialize the events list."""
        self._events: list[DomainEvent] = []

    def pull_events(self) -> list[DomainEvent]:
        """Return all collected events and clear the internal list.

        Returns:
            List of domain events emitted since last pull.
        """
        events, self._events = self._events, []
        return events


@dataclass(frozen=True)
class ValueObject:
    """Base class for value objects. Immutable and compared by value."""
