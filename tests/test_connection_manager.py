"""Tests for WebSocket ConnectionManager."""

from unittest.mock import AsyncMock

import pytest

from app.api.notifications.connection_manager import ConnectionManager


@pytest.mark.asyncio
async def test_connect_stores_websocket() -> None:
    """Test that connect stores the websocket for the user."""
    manager = ConnectionManager()
    ws = AsyncMock()

    await manager.connect("user-1", ws)

    assert "user-1" in manager.connections
    ws.accept.assert_awaited_once()


@pytest.mark.asyncio
async def test_disconnect_removes_websocket() -> None:
    """Test that disconnect removes the user from connections."""
    manager = ConnectionManager()
    ws = AsyncMock()
    await manager.connect("user-1", ws)

    manager.disconnect("user-1")

    assert "user-1" not in manager.connections


@pytest.mark.asyncio
async def test_disconnect_nonexistent_user_no_error() -> None:
    """Test that disconnecting a nonexistent user does not raise."""
    manager = ConnectionManager()
    manager.disconnect("nonexistent")


@pytest.mark.asyncio
async def test_send_to_online_user() -> None:
    """Test that send delivers data to a connected user."""
    manager = ConnectionManager()
    ws = AsyncMock()
    await manager.connect("user-1", ws)

    await manager.send("user-1", {"message": "hello"})

    ws.send_json.assert_awaited_once_with({"message": "hello"})


@pytest.mark.asyncio
async def test_send_to_offline_user_no_error() -> None:
    """Test that send to an offline user silently does nothing."""
    manager = ConnectionManager()
    await manager.send("offline-user", {"message": "hello"})


@pytest.mark.asyncio
async def test_send_stale_connection_cleans_up() -> None:
    """Test that a stale WebSocket connection is cleaned up on send failure."""
    manager = ConnectionManager()
    ws = AsyncMock()
    ws.send_json.side_effect = RuntimeError("connection closed")
    await manager.connect("user-1", ws)

    await manager.send("user-1", {"message": "hello"})

    assert "user-1" not in manager.connections
