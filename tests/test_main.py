"""Tests for main application endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root(client: AsyncClient) -> None:
    """Test root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    data: dict[str, str] = response.json()
    assert "message" in data
    assert "TaskHub" in data["message"]


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data: dict[str, str] = response.json()
    assert "status" in data
    assert "database" in data
