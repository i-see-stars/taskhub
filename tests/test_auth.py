"""Tests for authentication endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient

from app.api.auth.models import User
from app.api.auth.schemas import AccessTokenResponse, UserResponse


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    """Test user registration."""
    response = await client.post(
        "/auth/register",
        json={"email": "newuser@example.com", "password": "securepass123"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = UserResponse.model_validate(response.json())
    assert data.email == "newuser@example.com"
    assert data.user_id is not None
    # hashed_password is not in UserResponse, so this is implicit now


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user: User) -> None:
    """Test registration with duplicate email."""
    response = await client.post(
        "/auth/register",
        json={"email": test_user.email, "password": "anotherpass123"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User) -> None:
    """Test successful login."""
    response = await client.post(
        "/auth/access-token",
        data={"username": test_user.email, "password": "testpassword123"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = AccessTokenResponse.model_validate(response.json())
    assert data.access_token is not None
    assert data.refresh_token is not None
    assert data.token_type == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user: User) -> None:
    """Test login with wrong password."""
    response = await client.post(
        "/auth/access-token",
        data={"username": test_user.email, "password": "wrongpassword"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient) -> None:
    """Test login with non-existent user."""
    response = await client.post(
        "/auth/access-token",
        data={"username": "nonexistent@example.com", "password": "somepass"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_current_user(
    client: AsyncClient, auth_headers: dict[str, str], test_user: User
) -> None:
    """Test getting current user info."""
    response = await client.get("/auth/me", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = UserResponse.model_validate(response.json())
    assert data.email == test_user.email
    assert data.user_id == test_user.user_id


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient) -> None:
    """Test getting current user without authentication."""
    response = await client.get("/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user: User) -> None:
    """Test token refresh."""
    # First login
    login_response = await client.post(
        "/auth/access-token",
        data={"username": test_user.email, "password": "testpassword123"},
    )
    assert login_response.status_code == status.HTTP_200_OK
    refresh_token: str = login_response.json()["refresh_token"]

    # Refresh token
    response = await client.post(
        "/auth/refresh-token",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == status.HTTP_200_OK
    data = AccessTokenResponse.model_validate(response.json())
    assert data.access_token is not None
    assert data.refresh_token is not None


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient) -> None:
    """Test token refresh with invalid token."""
    response = await client.post(
        "/auth/refresh-token",
        json={"refresh_token": "invalid_token_here"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
