"""Tests for shared kernel base classes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.shared.domain.base import AggregateRoot, Entity, ValueObject
from app.shared.domain.events import DomainEvent
from app.shared.domain.identifiers import (
    CommentId,
    IssueId,
    NotificationId,
    ProjectId,
    UserId,
)


def test_entity_equality_by_id() -> None:
    """Test that entities with the same id are equal regardless of other fields."""

    @dataclass(eq=False)
    class MyEntity(Entity):
        id: str
        name: str

    e1 = MyEntity(id="1", name="Alice")
    e2 = MyEntity(id="1", name="Bob")  # same id, different name
    e3 = MyEntity(id="2", name="Alice")  # different id

    assert e1 == e2
    assert e1 != e3


def test_aggregate_root_collects_and_clears_events() -> None:
    """Test that aggregate root collects events and clears them after pull."""

    @dataclass(frozen=True)
    class MyEvent(DomainEvent):
        aggregate_id: str

    @dataclass(eq=False)
    class MyAggregate(AggregateRoot):
        id: str

    agg = MyAggregate(id="x")
    event = MyEvent(aggregate_id="x", occurred_at=datetime.now(UTC))
    agg._events.append(event)

    pulled = agg.pull_events()
    assert pulled == [event]
    assert agg.pull_events() == []  # cleared after pull


def test_value_object_equality_by_value() -> None:
    """Test that value objects with the same value are equal."""

    @dataclass(frozen=True)
    class Amount(ValueObject):
        value: int

    assert Amount(value=5) == Amount(value=5)
    assert Amount(value=5) != Amount(value=6)


def test_identifiers_are_value_objects() -> None:
    """Test that all domain identifiers behave as value objects."""
    assert UserId("a") == UserId("a")
    assert UserId("a") != UserId("b")
    assert IssueId("x") == IssueId("x")
    assert ProjectId("p") != ProjectId("q")
    assert CommentId("c") == CommentId("c")
    assert NotificationId("n") == NotificationId("n")
