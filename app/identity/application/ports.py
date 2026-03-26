"""Identity application ports (interfaces for infrastructure adapters).

These abstractions allow the application layer to depend on contracts
rather than concrete implementations like bcrypt or PyJWT.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AccessToken:
    """Represents a created access token — application-level, framework-free."""

    token: str
    expires_at: int


class PasswordHasher(ABC):
    """Port for password hashing and verification."""

    @abstractmethod
    def hash(self, password: str) -> str:
        """Hash a plaintext password.

        Args:
            password: Plaintext password.

        Returns:
            Hashed password string.
        """

    @abstractmethod
    def verify(self, password: str, hashed: str) -> bool:
        """Verify a plaintext password against a hash.

        Args:
            password: Plaintext password.
            hashed: Hashed password to verify against.

        Returns:
            True if match, False otherwise.
        """

    @abstractmethod
    def dummy_verify(self) -> None:
        """Perform a dummy hash check for timing-attack mitigation."""


class TokenService(ABC):
    """Port for JWT access token creation."""

    @abstractmethod
    def create_access_token(self, user_id: str) -> AccessToken:
        """Create a new access token for the given user.

        Args:
            user_id: The user's ID string.

        Returns:
            An AccessToken with the token string and expiry timestamp.
        """
