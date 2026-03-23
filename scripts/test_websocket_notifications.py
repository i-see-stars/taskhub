"""Manual WebSocket notification test.

This script tests the full notification flow end-to-end:
1. Registers two users (Bob = owner, Alice = assignee)
2. Bob creates a project and adds Alice
3. Alice connects via WebSocket
4. Bob creates an issue and assigns it to Alice
5. Alice receives a real-time WebSocket notification
6. Verifies the notification is also in the REST API

Usage:
    uv run python scripts/test_websocket_notifications.py

Requirements:
    - Server running at localhost:8000 (make run)
    - PostgreSQL running with migrations applied (make migrate)
    - websockets package (uv add --dev websockets)
"""

import asyncio
import json
import random
import string
import sys

import httpx
import websockets

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"


def log(step: str, detail: str = "") -> None:
    """Print a formatted log message."""
    prefix = f"\033[1;36m[{step}]\033[0m"
    print(f"{prefix} {detail}")


def success(msg: str) -> None:
    """Print a success message."""
    print(f"\033[1;32m  ✓ {msg}\033[0m")


def fail(msg: str) -> None:
    """Print a failure message and exit."""
    print(f"\033[1;31m  ✗ {msg}\033[0m")
    sys.exit(1)


async def register_user(client: httpx.AsyncClient, email: str, password: str) -> str:
    """Register a user and return their user_id."""
    resp = await client.post(
        f"{BASE_URL}/auth/register",
        json={"email": email, "password": password},
    )
    if resp.status_code == 201:
        user_id = resp.json()["user_id"]
        success(f"Registered {email} (id: {user_id[:8]}...)")
        return user_id
    if resp.status_code == 400:
        # User already exists — log in to get user_id
        token = await login_user(client, email, password)
        resp2 = await client.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        user_id = resp2.json()["user_id"]
        success(f"User {email} already exists (id: {user_id[:8]}...)")
        return user_id
    fail(f"Register failed: {resp.status_code} {resp.text}")
    return ""


async def login_user(client: httpx.AsyncClient, email: str, password: str) -> str:
    """Login and return access_token."""
    resp = await client.post(
        f"{BASE_URL}/auth/access-token",
        data={"username": email, "password": password},
    )
    if resp.status_code != 200:
        fail(f"Login failed for {email}: {resp.status_code} {resp.text}")
    token = resp.json()["access_token"]
    success(f"Logged in as {email}")
    return token


async def main() -> None:
    """Run the full WebSocket notification test."""
    print()
    print("=" * 60)
    print("  WebSocket Notification E2E Test")
    print("=" * 60)
    print()

    async with httpx.AsyncClient() as client:
        # --- Step 1: Register users ---
        log("Step 1", "Register two users")
        await register_user(client, "bob@test.com", "password123")
        alice_id = await register_user(client, "alice@test.com", "password123")

        # --- Step 2: Login both ---
        log("Step 2", "Login both users")
        bob_token = await login_user(client, "bob@test.com", "password123")
        alice_token = await login_user(client, "alice@test.com", "password123")

        bob_headers = {"Authorization": f"Bearer {bob_token}"}
        alice_headers = {"Authorization": f"Bearer {alice_token}"}

        # --- Step 3: Bob creates a project ---
        log("Step 3", "Bob creates a project")
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        project_key = f"WT{suffix}"
        resp = await client.post(
            f"{BASE_URL}/projects",
            headers=bob_headers,
            json={
                "name": f"WebSocket Test {suffix}",
                "key": project_key,
                "description": "Testing notifications",
            },
        )
        if resp.status_code != 201:
            fail(f"Create project failed: {resp.status_code} {resp.text}")
        project_id = resp.json()["project_id"]
        success(f"Project created (key: {project_key}, id: {project_id[:8]}...)")

        # --- Step 4: Bob adds Alice to the project ---
        log("Step 4", "Bob adds Alice as project member")
        resp = await client.post(
            f"{BASE_URL}/projects/{project_id}/members",
            headers=bob_headers,
            json={"user_id": alice_id, "role": "member"},
        )
        if resp.status_code != 201:
            fail(f"Add member failed: {resp.status_code} {resp.text}")
        success("Alice added as MEMBER")

        # --- Step 5: Bob creates an issue ---
        log("Step 5", "Bob creates an issue")
        resp = await client.post(
            f"{BASE_URL}/issues",
            headers=bob_headers,
            json={
                "title": "Fix WebSocket bug",
                "description": "Test notification delivery",
                "type": "task",
                "status": "todo",
                "priority": "high",
                "project_id": project_id,
            },
        )
        if resp.status_code != 201:
            fail(f"Create issue failed: {resp.status_code} {resp.text}")
        issue_id = resp.json()["issue_id"]
        success(f"Issue created (id: {issue_id[:8]}...)")

        # --- Step 6: Alice connects via WebSocket ---
        log("Step 6", "Alice connects via WebSocket")
        ws_received: list[dict[str, object]] = []

        async def listen_ws() -> None:
            """Listen for WebSocket messages."""
            uri = f"{WS_URL}/notifications/ws?token={alice_token}"
            async with websockets.connect(uri) as ws:
                success("WebSocket connected!")
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    data = json.loads(msg)
                    ws_received.append(data)
                    success(f"WebSocket received: {json.dumps(data, indent=2)}")
                except TimeoutError:
                    fail("Timed out waiting for WebSocket message (10s)")

        # Start WebSocket listener, wait a moment, then assign
        ws_task = asyncio.create_task(listen_ws())
        await asyncio.sleep(0.5)  # Give WebSocket time to connect

        # --- Step 7: Bob assigns issue to Alice (TRIGGERS NOTIFICATION) ---
        log("Step 7", "Bob assigns issue to Alice → should trigger notification")
        resp = await client.patch(
            f"{BASE_URL}/issues/{issue_id}",
            headers=bob_headers,
            json={"assignee_id": alice_id},
        )
        if resp.status_code != 200:
            fail(f"Assign failed: {resp.status_code} {resp.text}")
        success("Issue assigned to Alice")

        # Wait for WebSocket to receive
        await ws_task

        # --- Step 8: Verify via REST API ---
        log("Step 8", "Verify notification via REST API")
        resp = await client.get(
            f"{BASE_URL}/notifications",
            headers=alice_headers,
        )
        if resp.status_code != 200:
            fail(f"Get notifications failed: {resp.status_code} {resp.text}")
        notifications = resp.json()
        if notifications["total"] < 1:
            fail("No notifications found via REST API!")
        notification = notifications["notifications"][0]
        success(f"REST API shows {notifications['total']} notification(s)")
        success(f"  message: {notification['message']}")
        success(f"  is_read: {notification['is_read']}")
        success(f"  issue_id: {notification['issue_id']}")

        # --- Step 9: Mark as read ---
        log("Step 9", "Alice marks notification as read")
        notif_id = notification["notification_id"]
        resp = await client.patch(
            f"{BASE_URL}/notifications/{notif_id}/read",
            headers=alice_headers,
        )
        if resp.status_code != 200:
            fail(f"Mark read failed: {resp.status_code} {resp.text}")
        if resp.json()["is_read"] is not True:
            fail("is_read should be True after marking")
        success("Notification marked as read")

        # --- Step 10: Verify WebSocket received the message ---
        log("Step 10", "Verify WebSocket message content")
        if not ws_received:
            fail("No WebSocket messages received!")
        ws_msg = ws_received[0]
        if ws_msg.get("issue_id") != issue_id:
            fail(f"WebSocket issue_id mismatch: {ws_msg.get('issue_id')} != {issue_id}")
        success("WebSocket message matches issue_id")
        success(f"WebSocket message: {ws_msg.get('message')}")

    print()
    print("=" * 60)
    print("\033[1;32m  ALL TESTS PASSED!\033[0m")
    print("=" * 60)
    print()


if __name__ == "__main__":
    asyncio.run(main())
