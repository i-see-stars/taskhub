"""WebSocket connection manager."""

import logging

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections.

    Maps user IDs to their WebSocket connections for real-time push.
    Single instance per worker — does not support multi-worker setups.
    """

    def __init__(self) -> None:
        """Initialize with empty connections dict."""
        self.connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        """Accept and store a WebSocket connection.

        Args:
            user_id: The user's ID.
            websocket: The WebSocket connection to store.
        """
        await websocket.accept()
        self.connections[user_id] = websocket

    def disconnect(self, user_id: str) -> None:
        """Remove a user's WebSocket connection.

        Args:
            user_id: The user's ID to disconnect.
        """
        self.connections.pop(user_id, None)

    async def send(self, user_id: str, data: dict[str, object]) -> None:
        """Send JSON data to a user if they are connected.

        Silently handles offline users and stale connections.

        Args:
            user_id: The user's ID.
            data: JSON-serializable data to send.
        """
        websocket = self.connections.get(user_id)
        if websocket:
            try:
                await websocket.send_json(data)
            except WebSocketDisconnect, RuntimeError:
                logger.info("Stale WebSocket for user %s, cleaning up", user_id)
                self.disconnect(user_id)
