"""Tests for issues endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient

from app.api.auth.models import User
from app.api.issues.models import Issue
from app.api.issues.schemas import IssueListResponse, IssueResponse
from app.api.projects.models import Project


@pytest.mark.asyncio
async def test_create_issue(
    client: AsyncClient, auth_headers: dict[str, str], test_project: Project
) -> None:
    """Test creating a new issue."""
    response = await client.post(
        "/issues",
        headers=auth_headers,
        json={
            "title": "New Bug",
            "description": "Found a bug",
            "type": "bug",
            "status": "todo",
            "priority": "high",
            "project_id": test_project.project_id,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = IssueResponse.model_validate(response.json())
    assert data.title == "New Bug"
    assert data.type == "bug"
    assert data.priority == "high"
    assert data.issue_id is not None


@pytest.mark.asyncio
async def test_create_issue_invalid_project(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Test creating issue with non-existent project."""
    response = await client.post(
        "/issues",
        headers=auth_headers,
        json={
            "title": "Issue",
            "type": "task",
            "project_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_issue_unauthorized(
    client: AsyncClient, test_project: Project
) -> None:
    """Test creating issue without authentication."""
    response = await client.post(
        "/issues",
        json={
            "title": "Issue",
            "type": "task",
            "project_id": test_project.project_id,
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_issue_forbidden_for_viewer(
    client: AsyncClient,
    viewer_auth_headers: dict[str, str],
    test_project_with_viewer: Project,
) -> None:
    """Test that viewers cannot create issues."""
    response = await client.post(
        "/issues",
        headers=viewer_auth_headers,
        json={
            "title": "Sneaky Issue",
            "type": "task",
            "project_id": test_project_with_viewer.project_id,
        },
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_create_issue_with_parent(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_project: Project,
    test_issue: Issue,
) -> None:
    """Test creating issue with parent."""
    response = await client.post(
        "/issues",
        headers=auth_headers,
        json={
            "title": "Sub-task",
            "type": "task",
            "project_id": test_project.project_id,
            "parent_id": test_issue.issue_id,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = IssueResponse.model_validate(response.json())
    assert data.parent_id == test_issue.issue_id


@pytest.mark.asyncio
async def test_create_issue_assignee_not_member(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_project: Project,
    test_member_user: User,
) -> None:
    """Test that assigning a non-member returns 400."""
    response = await client.post(
        "/issues",
        headers=auth_headers,
        json={
            "title": "Assigned Issue",
            "type": "task",
            "project_id": test_project.project_id,
            "assignee_id": test_member_user.user_id,
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_create_issue_assignee_is_member(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_project_with_member: Project,
    test_member_user: User,
) -> None:
    """Test assigning an issue to a valid project member."""
    response = await client.post(
        "/issues",
        headers=auth_headers,
        json={
            "title": "Assigned Issue",
            "type": "task",
            "project_id": test_project_with_member.project_id,
            "assignee_id": test_member_user.user_id,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = IssueResponse.model_validate(response.json())
    assert data.assignee_id == test_member_user.user_id


@pytest.mark.asyncio
async def test_list_issues(
    client: AsyncClient, auth_headers: dict[str, str], test_issue: Issue
) -> None:
    """Test listing issues."""
    response = await client.get("/issues", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = IssueListResponse.model_validate(response.json())
    assert data.total >= 1
    assert any(i.issue_id == test_issue.issue_id for i in data.issues)


@pytest.mark.asyncio
async def test_list_issues_filtered_by_project(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_project: Project,
    test_issue: Issue,  # noqa: ARG001
) -> None:
    """Test listing issues filtered by project."""
    response = await client.get(
        f"/issues?project_id={test_project.project_id}", headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = IssueListResponse.model_validate(response.json())
    assert all(i.project_id == test_project.project_id for i in data.issues)


@pytest.mark.asyncio
async def test_list_issues_unauthorized(client: AsyncClient) -> None:
    """Test listing issues without authentication."""
    response = await client.get("/issues")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_issue(
    client: AsyncClient, auth_headers: dict[str, str], test_issue: Issue
) -> None:
    """Test getting a specific issue."""
    response = await client.get(f"/issues/{test_issue.issue_id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = IssueResponse.model_validate(response.json())
    assert data.issue_id == test_issue.issue_id
    assert data.title == test_issue.title


@pytest.mark.asyncio
async def test_get_issue_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Test getting non-existent issue."""
    response = await client.get(
        "/issues/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_issue(
    client: AsyncClient, auth_headers: dict[str, str], test_issue: Issue
) -> None:
    """Test updating an issue."""
    response = await client.patch(
        f"/issues/{test_issue.issue_id}",
        headers=auth_headers,
        json={"title": "Updated Issue Title", "status": "in_progress"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = IssueResponse.model_validate(response.json())
    assert data.title == "Updated Issue Title"
    assert data.status == "in_progress"


@pytest.mark.asyncio
async def test_update_issue_assignee_not_member(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_issue: Issue,
    test_member_user: User,
) -> None:
    """Test updating issue with assignee who is not a project member returns 400."""
    response = await client.patch(
        f"/issues/{test_issue.issue_id}",
        headers=auth_headers,
        json={"assignee_id": test_member_user.user_id},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_update_issue_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Test updating non-existent issue."""
    response = await client.patch(
        "/issues/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
        json={"title": "New Title"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_issue(
    client: AsyncClient, auth_headers: dict[str, str], test_issue: Issue
) -> None:
    """Test deleting an issue."""
    response = await client.delete(
        f"/issues/{test_issue.issue_id}", headers=auth_headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = await client.get(
        f"/issues/{test_issue.issue_id}", headers=auth_headers
    )
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_issue_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Test deleting non-existent issue."""
    response = await client.delete(
        "/issues/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
