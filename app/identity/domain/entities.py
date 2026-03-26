"""Identity domain entities."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.identity.domain.value_objects import Email, NotificationPreferences
from app.shared.domain.base import AggregateRoot, Entity
from app.shared.domain.identifiers import UserId


@dataclass(eq=False)
class User(AggregateRoot):
    """User aggregate root.

    Represents an authenticated identity. Notification preferences
    are composed via the NotificationPreferences value object.
    """

    id: UserId
    email: Email
    hashed_password: str
    preferences: NotificationPreferences = field(
        default_factory=lambda: NotificationPreferences(
            notify_in_app=True, notify_email=True
        )
    )


@dataclass(eq=False)
class RefreshToken(Entity):
    """Refresh token entity. Belongs to a User."""

    id: int
    token: str
    user_id: UserId
    used: bool
    exp: int
