"""Strongly-typed domain identifiers as value objects."""

from __future__ import annotations

from dataclasses import dataclass

from app.shared.domain.base import ValueObject


@dataclass(frozen=True)
class UserId(ValueObject):
    """Identity context user identifier."""

    value: str


@dataclass(frozen=True)
class ProjectId(ValueObject):
    """Issue tracking project identifier."""

    value: str


@dataclass(frozen=True)
class IssueId(ValueObject):
    """Issue tracking issue identifier."""

    value: str


@dataclass(frozen=True)
class CommentId(ValueObject):
    """Issue tracking comment identifier."""

    value: str


@dataclass(frozen=True)
class NotificationId(ValueObject):
    """Notifications context identifier."""

    value: str
