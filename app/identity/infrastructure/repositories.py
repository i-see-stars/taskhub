"""PostgreSQL implementations of identity repositories."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.entities import RefreshToken, User
from app.identity.domain.exceptions import TokenNotFound, UserNotFound
from app.identity.domain.repositories import RefreshTokenRepository, UserRepository
from app.identity.domain.value_objects import Email, NotificationPreferences
from app.identity.infrastructure.models import RefreshTokenModel, UserModel
from app.shared.domain.identifiers import UserId


class PostgresUserRepository(UserRepository):
    """User repository backed by PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a database session.

        Args:
            session: The async database session.
        """
        self._session = session

    def _to_domain(self, model: UserModel) -> User:
        """Map ORM UserModel to domain User entity.

        Args:
            model: The SQLAlchemy ORM model.

        Returns:
            The domain User aggregate.
        """
        return User(
            id=UserId(model.user_id),
            email=Email(value=model.email),
            hashed_password=model.hashed_password,
            preferences=NotificationPreferences(
                notify_in_app=model.notify_in_app,
                notify_email=model.notify_email,
            ),
        )

    def _to_model(self, entity: User, existing: UserModel | None = None) -> UserModel:
        """Map domain User entity to ORM UserModel.

        Args:
            entity: The domain User aggregate.
            existing: Existing ORM model to update, or None for new.

        Returns:
            The SQLAlchemy ORM model.
        """
        if existing is not None:
            existing.email = entity.email.value
            existing.hashed_password = entity.hashed_password
            existing.notify_in_app = entity.preferences.notify_in_app
            existing.notify_email = entity.preferences.notify_email
            return existing
        return UserModel(
            user_id=entity.id.value if entity.id.value else None,
            email=entity.email.value,
            hashed_password=entity.hashed_password,
            notify_in_app=entity.preferences.notify_in_app,
            notify_email=entity.preferences.notify_email,
        )

    async def get_by_id(self, user_id: UserId) -> User:
        """Fetch user by ID.

        Args:
            user_id: The user's unique identifier.

        Returns:
            The User aggregate.

        Raises:
            UserNotFound: If no user exists with this ID.
        """
        result = await self._session.execute(
            select(UserModel).where(UserModel.user_id == user_id.value)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise UserNotFound(f"User {user_id.value!r} not found")
        return self._to_domain(model)

    async def get_by_email(self, email: Email) -> User:
        """Fetch user by email.

        Args:
            email: The user's Email value object.

        Returns:
            The User aggregate.

        Raises:
            UserNotFound: If no user exists with this email.
        """
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email.value)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise UserNotFound(f"User with email {email.value!r} not found")
        return self._to_domain(model)

    async def save(self, user: User) -> User:
        """Persist new or updated user.

        Args:
            user: The User aggregate to save.

        Returns:
            Saved user with DB-assigned fields populated.
        """
        existing = None
        if user.id.value:
            result = await self._session.execute(
                select(UserModel).where(UserModel.user_id == user.id.value)
            )
            existing = result.scalar_one_or_none()
        model = self._to_model(user, existing)
        if existing is None:
            self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def delete(self, user_id: UserId) -> None:
        """Delete user by ID.

        Args:
            user_id: The user's unique identifier.
        """
        result = await self._session.execute(
            select(UserModel).where(UserModel.user_id == user_id.value)
        )
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)


class PostgresRefreshTokenRepository(RefreshTokenRepository):
    """RefreshToken repository backed by PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a database session.

        Args:
            session: The async database session.
        """
        self._session = session

    def _to_domain(self, model: RefreshTokenModel) -> RefreshToken:
        """Map ORM model to domain RefreshToken entity.

        Args:
            model: The SQLAlchemy ORM model.

        Returns:
            The domain RefreshToken entity.
        """
        return RefreshToken(
            id=model.id,
            token=model.refresh_token,
            user_id=UserId(model.user_id),
            used=model.used,
            exp=model.exp,
        )

    async def get_by_token(self, token: str) -> RefreshToken:
        """Fetch refresh token by value.

        Args:
            token: The token string.

        Returns:
            The RefreshToken entity.

        Raises:
            TokenNotFound: If the token is not found.
        """
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.refresh_token == token)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise TokenNotFound("Refresh token not found")
        return self._to_domain(model)

    async def save(self, token: RefreshToken) -> None:
        """Persist new or updated refresh token.

        Args:
            token: The RefreshToken entity to save.
        """
        if token.id:
            result = await self._session.execute(
                select(RefreshTokenModel).where(RefreshTokenModel.id == token.id)
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                existing.used = token.used
                await self._session.flush()
                return
        model = RefreshTokenModel(
            refresh_token=token.token,
            user_id=token.user_id.value,
            used=token.used,
            exp=token.exp,
        )
        self._session.add(model)
        await self._session.flush()

    async def delete_for_user(self, user_id: UserId) -> None:
        """Delete all refresh tokens for a user.

        Args:
            user_id: The user's unique identifier.
        """
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.user_id == user_id.value)
        )
        for model in result.scalars().all():
            await self._session.delete(model)
