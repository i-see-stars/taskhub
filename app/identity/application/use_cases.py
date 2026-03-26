"""Identity application use cases.

Each use case orchestrates: load → domain logic → save → commit.
Depends on domain abstractions and application ports only.
"""

from __future__ import annotations

import logging
import secrets
import time

from app.core.config import settings
from app.identity.application.ports import AccessToken, PasswordHasher, TokenService
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
from app.shared.domain.identifiers import UserId
from app.shared.domain.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


class RegisterUseCase:
    """Register a new user account."""

    def __init__(
        self,
        user_repo: UserRepository,
        uow: UnitOfWork,
        password_hasher: PasswordHasher,
    ) -> None:
        """Initialize with repositories, unit of work, and password hasher.

        Args:
            user_repo: User repository.
            uow: Unit of work for transaction management.
            password_hasher: Password hashing port.
        """
        self._user_repo = user_repo
        self._uow = uow
        self._password_hasher = password_hasher

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

        hashed = self._password_hasher.hash(password)
        user = User(
            id=UserId(""),  # DB assigns UUID on flush
            email=email_vo,
            hashed_password=hashed,
        )
        saved = await self._user_repo.save(user)
        await self._uow.commit()
        # TODO: emit UserRegistered event via event bus
        return saved


class AuthenticateUseCase:
    """Authenticate a user and return access + refresh tokens."""

    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
        uow: UnitOfWork,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        """Initialize with repositories, unit of work, and ports.

        Args:
            user_repo: User repository.
            token_repo: Refresh token repository.
            uow: Unit of work for transaction management.
            password_hasher: Password hashing port.
            token_service: Token creation port.
        """
        self._user_repo = user_repo
        self._token_repo = token_repo
        self._uow = uow
        self._password_hasher = password_hasher
        self._token_service = token_service

    async def execute(self, email: str, password: str) -> tuple[AccessToken, str, int]:
        """Authenticate and return (access_token, refresh_token_str, refresh_exp).

        Args:
            email: User's email address.
            password: Plaintext password.

        Returns:
            Tuple of (AccessToken, refresh_token_string, refresh_token_exp).

        Raises:
            InvalidCredentials: If credentials are wrong.
        """
        try:
            user = await self._user_repo.get_by_email(Email(value=email))
        except UserNotFound:
            # Timing-attack mitigation: run dummy hash even on miss
            self._password_hasher.dummy_verify()
            raise InvalidCredentials("Invalid credentials") from None

        if not self._password_hasher.verify(password, user.hashed_password):
            raise InvalidCredentials("Invalid credentials")

        access_token = self._token_service.create_access_token(user.id.value)
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
        await self._uow.commit()
        return access_token, refresh_token_str, exp


class RefreshTokenUseCase:
    """Exchange a refresh token for new access + refresh tokens."""

    def __init__(
        self,
        token_repo: RefreshTokenRepository,
        uow: UnitOfWork,
        token_service: TokenService,
    ) -> None:
        """Initialize.

        Args:
            token_repo: Refresh token repository.
            uow: Unit of work for transaction management.
            token_service: Token creation port.
        """
        self._token_repo = token_repo
        self._uow = uow
        self._token_service = token_service

    async def execute(self, refresh_token: str) -> tuple[AccessToken, str, int]:
        """Exchange refresh token for new tokens.

        Args:
            refresh_token: The refresh token string.

        Returns:
            Tuple of (AccessToken, new_refresh_token_str, exp).

        Raises:
            TokenNotFound: If token not found.
            TokenExpired: If token expired.
            TokenAlreadyUsed: If token already used.
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
        access_token = self._token_service.create_access_token(token.user_id.value)
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
        await self._uow.commit()
        return access_token, new_refresh_str, exp


class ChangePasswordUseCase:
    """Change the current user's password."""

    def __init__(
        self,
        user_repo: UserRepository,
        uow: UnitOfWork,
        password_hasher: PasswordHasher,
    ) -> None:
        """Initialize.

        Args:
            user_repo: User repository.
            uow: Unit of work for transaction management.
            password_hasher: Password hashing port.
        """
        self._user_repo = user_repo
        self._uow = uow
        self._password_hasher = password_hasher

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
            hashed_password=self._password_hasher.hash(new_password),
            preferences=user.preferences,
        )
        await self._user_repo.save(updated)
        await self._uow.commit()
        # TODO: emit PasswordChanged event via event bus


class DeleteAccountUseCase:
    """Delete the current user's account."""

    def __init__(self, user_repo: UserRepository, uow: UnitOfWork) -> None:
        """Initialize.

        Args:
            user_repo: User repository.
            uow: Unit of work for transaction management.
        """
        self._user_repo = user_repo
        self._uow = uow

    async def execute(self, user_id: UserId) -> None:
        """Delete a user account.

        Args:
            user_id: The user's ID to delete.
        """
        await self._user_repo.delete(user_id)
        await self._uow.commit()
