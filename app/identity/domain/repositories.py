"""Identity domain repository interfaces (ABCs)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.identity.domain.entities import RefreshToken, User
from app.shared.domain.identifiers import UserId


class UserRepository(ABC):
    """Abstract repository for User aggregate."""

    @abstractmethod
    async def get_by_id(self, user_id: UserId) -> User:
        """Fetch user by ID.

        Args:
            user_id: The user's unique identifier.

        Returns:
            The User aggregate.

        Raises:
            UserNotFound: If no user with this ID exists.
        """

    @abstractmethod
    async def get_by_email(self, email: str) -> User:
        """Fetch user by email.

        Args:
            email: The user's email address.

        Returns:
            The User aggregate.

        Raises:
            UserNotFound: If no user with this email exists.
        """

    @abstractmethod
    async def save(self, user: User) -> User:
        """Persist new or updated user.

        Args:
            user: The User aggregate to save.

        Returns:
            Saved user with any DB-assigned fields populated.
        """

    @abstractmethod
    async def delete(self, user_id: UserId) -> None:
        """Delete user by ID.

        Args:
            user_id: The user's unique identifier.
        """


class RefreshTokenRepository(ABC):
    """Abstract repository for RefreshToken entity."""

    @abstractmethod
    async def get_by_token(self, token: str) -> RefreshToken:
        """Fetch refresh token by value.

        Args:
            token: The token string.

        Returns:
            The RefreshToken entity.

        Raises:
            TokenNotFound: If the token is not found or has expired.
        """

    @abstractmethod
    async def save(self, token: RefreshToken) -> None:
        """Persist new or updated refresh token.

        Args:
            token: The RefreshToken entity to save.
        """

    @abstractmethod
    async def delete_for_user(self, user_id: UserId) -> None:
        """Delete all refresh tokens for a user.

        Args:
            user_id: The user's unique identifier.
        """
