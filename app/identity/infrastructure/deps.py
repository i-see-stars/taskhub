"""Identity FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.identity.infrastructure import api_messages
from app.identity.infrastructure.jwt import verify_jwt_token
from app.identity.infrastructure.models import UserModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/access-token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: AsyncSession = Depends(get_session),
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
