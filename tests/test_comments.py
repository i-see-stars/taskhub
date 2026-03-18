"""Tests for comments endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient

from app.api.comments.schemas import CommentListResponse, CommentResponse
from app.api.issues.models import Issue
from app.api.projects.models import Project


@pytest.mark.asyncio
async def test_create_comment(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_issue: Issue,
) -> None:
    """Test creating a comment on an issue."""
    response = await client.post(
        f"/issues/{test_issue.issue_id}/comments",
        headers=auth_headers,
        json={"body": "This is a comment."},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = CommentResponse.model_validate(response.json())
    assert data.body == "This is a comment."
    assert data.issue_id == test_issue.issue_id
    assert data.comment_id is not None


@pytest.mark.asyncio
async def test_create_comment_unauthorized(
    client: AsyncClient, test_issue: Issue
) -> None:
    """Test creating comment without authentication."""
    response = await client.post(
        f"/issues/{test_issue.issue_id}/comments",
        json={"body": "Anonymous comment"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_comment_forbidden_for_non_member(
    client: AsyncClient,
    member_auth_headers: dict[str, str],
    test_issue: Issue,
) -> None:
    """Test that non-members cannot comment on issues."""
    response = await client.post(
        f"/issues/{test_issue.issue_id}/comments",
        headers=member_auth_headers,
        json={"body": "I should not be allowed"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_create_comment_forbidden_for_viewer(
    client: AsyncClient,
    viewer_auth_headers: dict[str, str],
    test_project_with_viewer: Project,  # noqa: ARG001
    test_issue: Issue,
) -> None:
    """Test that viewers cannot create comments."""
    response = await client.post(
        f"/issues/{test_issue.issue_id}/comments",
        headers=viewer_auth_headers,
        json={"body": "Viewer trying to comment"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_list_comments(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_issue: Issue,
) -> None:
    """Test listing comments on an issue."""
    # Create a comment first
    await client.post(
        f"/issues/{test_issue.issue_id}/comments",
        headers=auth_headers,
        json={"body": "First comment"},
    )

    response = await client.get(
        f"/issues/{test_issue.issue_id}/comments",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = CommentListResponse.model_validate(response.json())
    assert data.total >= 1
    assert any(c.body == "First comment" for c in data.comments)


@pytest.mark.asyncio
async def test_list_comments_as_member(
    client: AsyncClient,
    member_auth_headers: dict[str, str],
    test_project_with_member: Project,  # noqa: ARG001
    test_issue: Issue,
) -> None:
    """Test that project members can list comments."""
    response = await client.get(
        f"/issues/{test_issue.issue_id}/comments",
        headers=member_auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_delete_comment_by_author(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_issue: Issue,
) -> None:
    """Test that comment author can delete their own comment."""
    create_response = await client.post(
        f"/issues/{test_issue.issue_id}/comments",
        headers=auth_headers,
        json={"body": "Comment to delete"},
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    comment_id = create_response.json()["comment_id"]

    response = await client.delete(
        f"/issues/{test_issue.issue_id}/comments/{comment_id}",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_delete_comment_by_non_author_forbidden(
    client: AsyncClient,
    auth_headers: dict[str, str],
    member_auth_headers: dict[str, str],
    test_project_with_member: Project,  # noqa: ARG001
    test_issue: Issue,
) -> None:
    """Test that a non-author member cannot delete another user's comment."""
    # Owner creates the comment
    create_response = await client.post(
        f"/issues/{test_issue.issue_id}/comments",
        headers=auth_headers,
        json={"body": "Owner's comment"},
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    comment_id = create_response.json()["comment_id"]

    # Member tries to delete it
    response = await client.delete(
        f"/issues/{test_issue.issue_id}/comments/{comment_id}",
        headers=member_auth_headers,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_delete_comment_not_found(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_issue: Issue,
) -> None:
    """Test deleting non-existent comment."""
    response = await client.delete(
        f"/issues/{test_issue.issue_id}/comments/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
