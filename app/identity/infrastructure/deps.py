"""Identity FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.identity.application.use_cases import (
    AuthenticateUseCase,
    ChangePasswordUseCase,
    DeleteAccountUseCase,
    RefreshTokenUseCase,
    RegisterUseCase,
)
from app.identity.infrastructure import api_messages
from app.identity.infrastructure.adapters import BcryptPasswordHasher, JWTTokenService
from app.identity.infrastructure.jwt import verify_jwt_token
from app.identity.infrastructure.models import UserModel
from app.identity.infrastructure.repositories import (
    PostgresRefreshTokenRepository,
    PostgresUserRepository,
)
from app.shared.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/access-token")

_password_hasher = BcryptPasswordHasher()
_token_service = JWTTokenService()


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserModel:
    """Get the current authenticated user from the JWT token.

    Args:
        token: The OAuth2 bearer token.
        session: Database session.

    Returns:
        The authenticated UserModel.

    Raises:
        HTTPException: If the user is not found or token is invalid.
    """
    token_payload = verify_jwt_token(token)

    user = await session.scalar(
        select(UserModel).where(UserModel.user_id == token_payload.sub)
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_messages.JWT_ERROR_USER_REMOVED,
        )
    return user


def get_register_use_case(
    session: AsyncSession = Depends(get_session),
) -> RegisterUseCase:
    """Create RegisterUseCase with injected dependencies.

    Args:
        session: Database session.

    Returns:
        Configured RegisterUseCase instance.
    """
    return RegisterUseCase(
        user_repo=PostgresUserRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
        password_hasher=_password_hasher,
    )


def get_authenticate_use_case(
    session: AsyncSession = Depends(get_session),
) -> AuthenticateUseCase:
    """Create AuthenticateUseCase with injected dependencies.

    Args:
        session: Database session.

    Returns:
        Configured AuthenticateUseCase instance.
    """
    return AuthenticateUseCase(
        user_repo=PostgresUserRepository(session),
        token_repo=PostgresRefreshTokenRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
        password_hasher=_password_hasher,
        token_service=_token_service,
    )


def get_refresh_token_use_case(
    session: AsyncSession = Depends(get_session),
) -> RefreshTokenUseCase:
    """Create RefreshTokenUseCase with injected dependencies.

    Args:
        session: Database session.

    Returns:
        Configured RefreshTokenUseCase instance.
    """
    return RefreshTokenUseCase(
        token_repo=PostgresRefreshTokenRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
        token_service=_token_service,
    )


def get_change_password_use_case(
    session: AsyncSession = Depends(get_session),
) -> ChangePasswordUseCase:
    """Create ChangePasswordUseCase with injected dependencies.

    Args:
        session: Database session.

    Returns:
        Configured ChangePasswordUseCase instance.
    """
    return ChangePasswordUseCase(
        user_repo=PostgresUserRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
        password_hasher=_password_hasher,
    )


def get_delete_account_use_case(
    session: AsyncSession = Depends(get_session),
) -> DeleteAccountUseCase:
    """Create DeleteAccountUseCase with injected dependencies.

    Args:
        session: Database session.

    Returns:
        Configured DeleteAccountUseCase instance.
    """
    return DeleteAccountUseCase(
        user_repo=PostgresUserRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )
