"""Identity domain entities."""

from __future__ import annotations

from dataclasses import dataclass

from app.shared.domain.base import AggregateRoot, Entity
from app.shared.domain.identifiers import UserId


@dataclass(eq=False)
class User(AggregateRoot):
    """User aggregate root.

    Represents an authenticated identity. Notification preferences
    are stored directly on the user for now (no separate settings aggregate).
    """

    id: UserId
    email: str
    hashed_password: str
    notify_in_app: bool = True
    notify_email: bool = False


@dataclass(eq=False)
class RefreshToken(Entity):
    """Refresh token entity. Belongs to a User."""

    id: int
    token: str
    user_id: UserId
    used: bool
    exp: int
