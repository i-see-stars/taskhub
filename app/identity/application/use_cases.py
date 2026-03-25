"""Identity application use cases.

Each use case orchestrates: load → domain logic → save → commit.
No HTTP or ORM framework knowledge — depends on domain abstractions only.
"""

from __future__ import annotations

import logging
import secrets
import time

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.core.config import settings  # updated to app.core.config in Task 13
from app.identity.domain.entities import RefreshToken, User
from app.identity.domain.exceptions import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    TokenAlreadyUsed,
    TokenExpired,
    UserNotFound,
)
from app.identity.domain.repositories import RefreshTokenRepository, UserRepository
from app.identity.domain.value_objects import Email
from app.identity.infrastructure.jwt import JWTToken, create_jwt_token
from app.identity.infrastructure.password import (
    DUMMY_PASSWORD,
    get_password_hash,
    verify_password,
)
from app.shared.domain.identifiers import UserId

logger = logging.getLogger(__name__)


class RegisterUseCase:
    """Register a new user account."""

    def __init__(self, user_repo: UserRepository, session: AsyncSession) -> None:
        """Initialize with repositories and session.

        Args:
            user_repo: User repository.
            session: Database session for committing.
        """
        self._user_repo = user_repo
        self._session = session

    async def execute(self, email: str, password: str) -> User:
        """Register a new user.

        Args:
            email: User's email address (plain string — validated here).
            password: Plaintext password.

        Returns:
            Newly created User domain entity.

        Raises:
            EmailAlreadyRegistered: If email is already in use.
        """
        email_vo = Email(value=email)  # validates format
        try:
            await self._user_repo.get_by_email(email_vo)
            raise EmailAlreadyRegistered(email)
        except UserNotFound:
            pass

        hashed = get_password_hash(password)
        user = User(
            id=UserId(""),  # DB assigns UUID on flush
            email=email_vo,
            hashed_password=hashed,
        )
        try:
            saved = await self._user_repo.save(user)
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise EmailAlreadyRegistered(email) from None
        # TODO: emit UserRegistered event via event bus
        return saved


class AuthenticateUseCase:
    """Authenticate a user and return access + refresh tokens."""

    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
        session: AsyncSession,
    ) -> None:
        """Initialize with repositories and session.

        Args:
            user_repo: User repository.
            token_repo: Refresh token repository.
            session: Database session for committing.
        """
        self._user_repo = user_repo
        self._token_repo = token_repo
        self._session = session

    async def execute(self, email: str, password: str) -> tuple[JWTToken, str, int]:
        """Authenticate and return (jwt_token, refresh_token_str, refresh_token_exp).

        Args:
            email: User's email address.
            password: Plaintext password.

        Returns:
            Tuple of (JWTToken, refresh_token_string, refresh_token_exp_timestamp).

        Raises:
            InvalidCredentials: If credentials are wrong.
        """
        try:
            user = await self._user_repo.get_by_email(Email(value=email))
        except UserNotFound:
            # Timing-attack mitigation: run dummy hash even on miss
            verify_password("dummy", DUMMY_PASSWORD)
            raise InvalidCredentials("Invalid credentials") from None

        if not verify_password(password, user.hashed_password):
            raise InvalidCredentials("Invalid credentials")

        jwt_token = create_jwt_token(user_id=user.id.value)
        refresh_token_str = secrets.token_urlsafe(32)
        exp = int(time.time() + settings.jwt_refresh_token_expire_secs)

        token_entity = RefreshToken(
            id=0,  # DB auto-assigns
            token=refresh_token_str,
            user_id=user.id,
            used=False,
            exp=exp,
        )
        await self._token_repo.save(token_entity)
        await self._session.commit()
        return jwt_token, refresh_token_str, exp


class RefreshTokenUseCase:
    """Exchange a refresh token for new access + refresh tokens."""

    def __init__(
        self,
        token_repo: RefreshTokenRepository,
        session: AsyncSession,
    ) -> None:
        """Initialize.

        Args:
            token_repo: Refresh token repository.
            session: Database session.
        """
        self._token_repo = token_repo
        self._session = session

    async def execute(self, refresh_token: str) -> tuple[JWTToken, str, int]:
        """Exchange refresh token for new tokens.

        Args:
            refresh_token: The refresh token string.

        Returns:
            Tuple of (JWTToken, new_refresh_token_str, exp).

        Raises:
            TokenNotFound: If token not found.
            InvalidCredentials: If token expired or already used.
        """
        token = await self._token_repo.get_by_token(refresh_token)

        if time.time() > token.exp:
            raise TokenExpired("Refresh token expired")
        if token.used:
            raise TokenAlreadyUsed("Refresh token already used")

        # Mark old token used
        used_token = RefreshToken(
            id=token.id,
            token=token.token,
            user_id=token.user_id,
            used=True,
            exp=token.exp,
        )
        await self._token_repo.save(used_token)

        # Issue new token
        jwt_token = create_jwt_token(user_id=token.user_id.value)
        new_refresh_str = secrets.token_urlsafe(32)
        exp = int(time.time() + settings.jwt_refresh_token_expire_secs)

        new_token = RefreshToken(
            id=0,
            token=new_refresh_str,
            user_id=token.user_id,
            used=False,
            exp=exp,
        )
        await self._token_repo.save(new_token)
        await self._session.commit()
        return jwt_token, new_refresh_str, exp


class ChangePasswordUseCase:
    """Change the current user's password."""

    def __init__(self, user_repo: UserRepository, session: AsyncSession) -> None:
        """Initialize.

        Args:
            user_repo: User repository.
            session: Database session.
        """
        self._user_repo = user_repo
        self._session = session

    async def execute(self, user_id: UserId, new_password: str) -> None:
        """Change user's password.

        Args:
            user_id: The user's ID.
            new_password: The new plaintext password.
        """
        user = await self._user_repo.get_by_id(user_id)
        updated = User(
            id=user.id,
            email=user.email,
            hashed_password=get_password_hash(new_password),
            preferences=user.preferences,
        )
        await self._user_repo.save(updated)
        await self._session.commit()
        # TODO: emit PasswordChanged event via event bus


class DeleteAccountUseCase:
    """Delete the current user's account."""

    def __init__(self, user_repo: UserRepository, session: AsyncSession) -> None:
        """Initialize.

        Args:
            user_repo: User repository.
            session: Database session.
        """
        self._user_repo = user_repo
        self._session = session

    async def execute(self, user_id: UserId) -> None:
        """Delete a user account.

        Args:
            user_id: The user's ID to delete.
        """
        await self._user_repo.delete(user_id)
        await self._session.commit()
