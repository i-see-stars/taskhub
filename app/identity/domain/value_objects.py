"""Identity domain value objects."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.identity.domain.exceptions import InvalidEmail
from app.shared.domain.base import ValueObject

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class Email(ValueObject):
    """Validated email address.

    Raises:
        InvalidEmail: If the format is invalid.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate email format on construction.

        Raises:
            InvalidEmail: If value does not match the email pattern.
        """
        if not _EMAIL_RE.match(self.value):
            raise InvalidEmail(f"Invalid email address: {self.value!r}")


@dataclass(frozen=True)
class NotificationPreferences(ValueObject):
    """User notification channel preferences."""

    notify_in_app: bool
    notify_email: bool
