"""Tests for WebSocket notification push."""

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.auth.jwt import create_jwt_token
from app.api.main import app
from app.api.notifications.connection_manager import ConnectionManager
from app.api.notifications.deps import get_connection_manager


def test_websocket_connect_with_valid_token() -> None:
    """Test WebSocket connection with a valid JWT token."""
    token = create_jwt_token(user_id="test-user-id")
    _connection_manager = ConnectionManager()
    app.dependency_overrides[get_connection_manager] = lambda: _connection_manager

    try:
        with (
            TestClient(app) as sync_client,
            sync_client.websocket_connect(
                f"/notifications/ws?token={token.access_token}"
            ) as _ws,
        ):
            # Connection established — just verify it doesn't crash
            pass
    finally:
        app.dependency_overrides.pop(get_connection_manager, None)


def test_websocket_reject_invalid_token() -> None:
    """Test WebSocket connection rejected with invalid token."""
    _connection_manager = ConnectionManager()
    app.dependency_overrides[get_connection_manager] = lambda: _connection_manager

    try:
        with (
            TestClient(app) as sync_client,
            pytest.raises(WebSocketDisconnect),
            sync_client.websocket_connect("/notifications/ws?token=invalid-token"),
        ):
            pass
    finally:
        app.dependency_overrides.pop(get_connection_manager, None)
