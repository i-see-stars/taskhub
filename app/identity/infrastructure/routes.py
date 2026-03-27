"""Identity API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

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
from app.identity.infrastructure.deps import (
    get_authenticate_use_case,
    get_change_password_use_case,
    get_current_user,
    get_delete_account_use_case,
    get_refresh_token_use_case,
    get_register_use_case,
)
from app.identity.infrastructure.models import UserModel
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
    use_case: DeleteAccountUseCase = Depends(get_delete_account_use_case),
) -> None:
    """Delete the current user's account."""
    await use_case.execute(UserId(current_user.user_id))


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Update current user password",
)
async def reset_current_user_password(
    user_update_password: UserUpdatePasswordRequest,
    current_user: UserModel = Depends(get_current_user),
    use_case: ChangePasswordUseCase = Depends(get_change_password_use_case),
) -> None:
    """Update the current user's password."""
    await use_case.execute(UserId(current_user.user_id), user_update_password.password)


@router.post(
    "/access-token",
    response_model=AccessTokenResponse,
    responses=api_messages.ACCESS_TOKEN_RESPONSES,
    description="OAuth2 compatible token, get an access token for future requests using username and password",
)
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    use_case: AuthenticateUseCase = Depends(get_authenticate_use_case),
) -> AccessTokenResponse:
    """Login with email and password to get an access token."""
    try:
        access_token, refresh_token_str, refresh_exp = await use_case.execute(
            email=form_data.username,
            password=form_data.password,
        )
    except InvalidCredentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_messages.PASSWORD_INVALID,
        ) from None
    return AccessTokenResponse(
        access_token=access_token.token,
        expires_at=access_token.expires_at,
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
    use_case: RefreshTokenUseCase = Depends(get_refresh_token_use_case),
) -> AccessTokenResponse:
    """Refresh an access token using a refresh token."""
    try:
        access_token, new_refresh_str, refresh_exp = await use_case.execute(
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
        access_token=access_token.token,
        expires_at=access_token.expires_at,
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
    use_case: RegisterUseCase = Depends(get_register_use_case),
) -> UserResponse:
    """Register a new user account."""
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
    return UserResponse(
        user_id=user_entity.id.value, email=str(user_entity.email.value)
    )
