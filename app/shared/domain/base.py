"""Shared kernel base classes for DDD building blocks."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from app.shared.domain.events import DomainEvent


@dataclass(eq=False)
class Entity:
    """Base class for domain entities. Equality is based on identity, not value."""

    def __eq__(self, other: object) -> bool:
        """Compare by the field named 'id', falling back to first field.

        Args:
            other: The object to compare.

        Returns:
            True if both entities have the same identity.
        """
        if not isinstance(other, self.__class__):
            return False
        fields = dataclasses.fields(self)
        id_field_name = next(
            (f.name for f in fields if f.name == "id"),
            fields[0].name if fields else None,
        )
        if id_field_name is None:
            return self is other
        return bool(getattr(self, id_field_name) == getattr(other, id_field_name))

    def __hash__(self) -> int:
        """Hash by the field named 'id', falling back to first field.

        Returns:
            Hash of the identity field value.
        """
        fields = dataclasses.fields(self)
        id_field_name = next(
            (f.name for f in fields if f.name == "id"),
            fields[0].name if fields else None,
        )
        if id_field_name is None:
            return hash(id(self))
        return hash(getattr(self, id_field_name))


@dataclass(eq=False)
class AggregateRoot(Entity):
    """Base class for aggregate roots. Collects domain events for publication."""

    def __post_init__(self) -> None:
        """Initialize the events list."""
        self._events: list[DomainEvent] = []

    def _register_event(self, event: DomainEvent) -> None:
        """Add a domain event to the pending events list.

        Args:
            event: The domain event to register.
        """
        self._events.append(event)

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
