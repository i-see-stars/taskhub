"""Tests for projects endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.models import User
from app.api.projects.models import Project
from app.api.projects.schemas import (
    ProjectListResponse,
    ProjectMemberResponse,
    ProjectMembersListResponse,
    ProjectResponse,
)


@pytest.mark.asyncio
async def test_create_project(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Test creating a new project."""
    response = await client.post(
        "/projects",
        headers=auth_headers,
        json={
            "name": "My Project",
            "description": "A cool project",
            "key": "MYPROJ",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = ProjectResponse.model_validate(response.json())
    assert data.name == "My Project"
    assert data.key == "MYPROJ"
    assert data.project_id is not None


@pytest.mark.asyncio
async def test_create_project_duplicate_key(
    client: AsyncClient, auth_headers: dict[str, str], test_project: Project
) -> None:
    """Test creating project with duplicate key."""
    response = await client.post(
        "/projects",
        headers=auth_headers,
        json={
            "name": "Another Project",
            "description": "Description",
            "key": test_project.key,
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_create_project_unauthorized(client: AsyncClient) -> None:
    """Test creating project without authentication."""
    response = await client.post(
        "/projects",
        json={"name": "Project", "key": "PROJ"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_list_projects(
    client: AsyncClient, auth_headers: dict[str, str], test_project: Project
) -> None:
    """Test listing projects returns projects where user is a member."""
    response = await client.get("/projects", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = ProjectListResponse.model_validate(response.json())
    assert data.total >= 1
    assert any(p.project_id == test_project.project_id for p in data.projects)


@pytest.mark.asyncio
async def test_list_projects_excludes_non_member(
    client: AsyncClient,
    member_auth_headers: dict[str, str],
    test_project: Project,
) -> None:
    """Test that non-members do not see the project in their list."""
    response = await client.get("/projects", headers=member_auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = ProjectListResponse.model_validate(response.json())
    assert not any(p.project_id == test_project.project_id for p in data.projects)


@pytest.mark.asyncio
async def test_list_projects_unauthorized(client: AsyncClient) -> None:
    """Test listing projects without authentication."""
    response = await client.get("/projects")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_project(
    client: AsyncClient, auth_headers: dict[str, str], test_project: Project
) -> None:
    """Test getting a specific project."""
    response = await client.get(
        f"/projects/{test_project.project_id}", headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = ProjectResponse.model_validate(response.json())
    assert data.project_id == test_project.project_id
    assert data.name == test_project.name


@pytest.mark.asyncio
async def test_get_project_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Test getting non-existent project returns 404."""
    response = await client.get(
        "/projects/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_project_forbidden_for_non_member(
    client: AsyncClient,
    member_auth_headers: dict[str, str],
    test_project: Project,
) -> None:
    """Test that a non-member cannot access a project."""
    response = await client.get(
        f"/projects/{test_project.project_id}", headers=member_auth_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_update_project(
    client: AsyncClient, auth_headers: dict[str, str], test_project: Project
) -> None:
    """Test updating a project as owner."""
    response = await client.patch(
        f"/projects/{test_project.project_id}",
        headers=auth_headers,
        json={"name": "Updated Project Name"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = ProjectResponse.model_validate(response.json())
    assert data.name == "Updated Project Name"
    assert data.project_id == test_project.project_id


@pytest.mark.asyncio
async def test_update_project_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Test updating non-existent project."""
    response = await client.patch(
        "/projects/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
        json={"name": "New Name"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_project_forbidden_for_viewer(
    client: AsyncClient,
    viewer_auth_headers: dict[str, str],
    test_project_with_viewer: Project,
) -> None:
    """Test that viewers cannot update a project."""
    response = await client.patch(
        f"/projects/{test_project_with_viewer.project_id}",
        headers=viewer_auth_headers,
        json={"name": "Hacked Name"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_delete_project(
    client: AsyncClient, auth_headers: dict[str, str], test_project: Project
) -> None:
    """Test deleting a project as owner."""
    response = await client.delete(
        f"/projects/{test_project.project_id}", headers=auth_headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = await client.get(
        f"/projects/{test_project.project_id}", headers=auth_headers
    )
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_project_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Test deleting non-existent project."""
    response = await client.delete(
        "/projects/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_project_forbidden_for_member(
    client: AsyncClient,
    member_auth_headers: dict[str, str],
    test_project_with_member: Project,
) -> None:
    """Test that non-owners cannot delete a project."""
    response = await client.delete(
        f"/projects/{test_project_with_member.project_id}",
        headers=member_auth_headers,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- Member management tests ---


@pytest.mark.asyncio
async def test_list_members(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_project: Project,
) -> None:
    """Test listing project members."""
    response = await client.get(
        f"/projects/{test_project.project_id}/members", headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = ProjectMembersListResponse.model_validate(response.json())
    assert data.total >= 1


@pytest.mark.asyncio
async def test_add_member(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_project: Project,
    test_member_user: User,
) -> None:
    """Test adding a member to a project as owner."""
    response = await client.post(
        f"/projects/{test_project.project_id}/members",
        headers=auth_headers,
        json={"user_id": test_member_user.user_id, "role": "member"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = ProjectMemberResponse.model_validate(response.json())
    assert data.user_id == test_member_user.user_id
    assert data.role == "member"


@pytest.mark.asyncio
async def test_add_member_forbidden_for_non_owner(
    client: AsyncClient,
    member_auth_headers: dict[str, str],
    test_project_with_member: Project,
    test_viewer_user: User,
) -> None:
    """Test that non-owners cannot add members."""
    response = await client.post(
        f"/projects/{test_project_with_member.project_id}/members",
        headers=member_auth_headers,
        json={"user_id": test_viewer_user.user_id, "role": "viewer"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_add_member_duplicate(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_project_with_member: Project,
    test_member_user: User,
) -> None:
    """Test adding an already existing member returns 400."""
    response = await client.post(
        f"/projects/{test_project_with_member.project_id}/members",
        headers=auth_headers,
        json={"user_id": test_member_user.user_id, "role": "member"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_remove_member(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_project_with_member: Project,
    test_member_user: User,
) -> None:
    """Test removing a member as owner."""
    response = await client.delete(
        f"/projects/{test_project_with_member.project_id}/members/{test_member_user.user_id}",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_remove_last_owner_forbidden(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_project: Project,
    test_user: User,
    db_session: AsyncSession,  # noqa: ARG001
) -> None:
    """Test that removing the last owner is not allowed."""
    response = await client.delete(
        f"/projects/{test_project.project_id}/members/{test_user.user_id}",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
