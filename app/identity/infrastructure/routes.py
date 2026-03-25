"""Identity API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.core.database import get_session  # updated to app.core in Task 13
from app.identity.application.use_cases import (
    AuthenticateUseCase,
    ChangePasswordUseCase,
    DeleteAccountUseCase,
    RefreshTokenUseCase,
    RegisterUseCase,
)
from app.identity.domain.exceptions import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    TokenAlreadyUsed,
    TokenExpired,
    TokenNotFound,
)
from app.identity.infrastructure import api_messages
from app.identity.infrastructure.deps import get_current_user
from app.identity.infrastructure.models import UserModel
from app.identity.infrastructure.repositories import (
    PostgresRefreshTokenRepository,
    PostgresUserRepository,
)
from app.identity.infrastructure.schemas import (
    AccessTokenResponse,
    RefreshTokenRequest,
    UserCreateRequest,
    UserResponse,
    UserUpdatePasswordRequest,
)
from app.shared.domain.identifiers import UserId

router = APIRouter(responses=api_messages.UNAUTHORIZED_RESPONSES)


@router.get("/me", response_model=UserResponse, description="Get current user")
async def read_current_user(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """Get the currently authenticated user."""
    return current_user


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete current user",
)
async def delete_current_user(
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete the current user's account."""
    use_case = DeleteAccountUseCase(
        user_repo=PostgresUserRepository(session),
        session=session,
    )
    await use_case.execute(UserId(current_user.user_id))


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Update current user password",
)
async def reset_current_user_password(
    user_update_password: UserUpdatePasswordRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    """Update the current user's password."""
    use_case = ChangePasswordUseCase(
        user_repo=PostgresUserRepository(session),
        session=session,
    )
    await use_case.execute(UserId(current_user.user_id), user_update_password.password)


@router.post(
    "/access-token",
    response_model=AccessTokenResponse,
    responses=api_messages.ACCESS_TOKEN_RESPONSES,
    description="OAuth2 compatible token, get an access token for future requests using username and password",
)
async def login_access_token(
    session: AsyncSession = Depends(get_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> AccessTokenResponse:
    """Login with email and password to get an access token."""
    use_case = AuthenticateUseCase(
        user_repo=PostgresUserRepository(session),
        token_repo=PostgresRefreshTokenRepository(session),
        session=session,
    )
    try:
        jwt_token, refresh_token_str, refresh_exp = await use_case.execute(
            email=form_data.username,
            password=form_data.password,
        )
    except InvalidCredentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_messages.PASSWORD_INVALID,
        ) from None
    return AccessTokenResponse(
        access_token=jwt_token.access_token,
        expires_at=jwt_token.payload.exp,
        refresh_token=refresh_token_str,
        refresh_token_expires_at=refresh_exp,
    )


@router.post(
    "/refresh-token",
    response_model=AccessTokenResponse,
    responses=api_messages.REFRESH_TOKEN_RESPONSES,
    description="OAuth2 compatible token, get an access token for future requests using refresh token",
)
async def refresh_token(
    data: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session),
) -> AccessTokenResponse:
    """Refresh an access token using a refresh token."""
    use_case = RefreshTokenUseCase(
        token_repo=PostgresRefreshTokenRepository(session),
        session=session,
    )
    try:
        jwt_token, new_refresh_str, refresh_exp = await use_case.execute(
            data.refresh_token
        )
    except TokenNotFound:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_messages.REFRESH_TOKEN_NOT_FOUND,
        ) from None
    except TokenExpired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.REFRESH_TOKEN_EXPIRED,
        ) from None
    except TokenAlreadyUsed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.REFRESH_TOKEN_ALREADY_USED,
        ) from None
    return AccessTokenResponse(
        access_token=jwt_token.access_token,
        expires_at=jwt_token.payload.exp,
        refresh_token=new_refresh_str,
        refresh_token_expires_at=refresh_exp,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    description="Create new user",
    status_code=status.HTTP_201_CREATED,
)
async def register_new_user(
    new_user: UserCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> UserModel:
    """Register a new user account."""
    use_case = RegisterUseCase(
        user_repo=PostgresUserRepository(session),
        session=session,
    )
    try:
        user_entity = await use_case.execute(
            email=str(new_user.email),
            password=new_user.password,
        )
    except EmailAlreadyRegistered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.EMAIL_ADDRESS_ALREADY_USED,
        ) from None
    # Fetch the ORM model for response serialization
    result = await session.execute(
        select(UserModel).where(UserModel.user_id == user_entity.id.value)
    )
    return result.scalar_one()
