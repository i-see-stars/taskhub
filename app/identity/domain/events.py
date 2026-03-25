"""Identity domain events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.shared.domain.events import DomainEvent
from app.shared.domain.identifiers import UserId


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    """Emitted when a new user registers."""

    user_id: UserId
    email: str
    occurred_at: datetime


@dataclass(frozen=True)
class PasswordChanged(DomainEvent):
    """Emitted when a user changes their password."""

    user_id: UserId
    occurred_at: datetime
