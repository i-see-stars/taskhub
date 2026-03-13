"""Tests for projects endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient

from app.api.projects.models import Project


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, auth_headers: dict):
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
    data = response.json()
    assert data["name"] == "My Project"
    assert data["key"] == "MYPROJ"
    assert "project_id" in data


@pytest.mark.asyncio
async def test_create_project_duplicate_key(
    client: AsyncClient, auth_headers: dict, test_project: Project
):
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
async def test_create_project_unauthorized(client: AsyncClient):
    """Test creating project without authentication."""
    response = await client.post(
        "/projects",
        json={"name": "Project", "key": "PROJ"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_list_projects(
    client: AsyncClient, auth_headers: dict, test_project: Project
):
    """Test listing projects."""
    response = await client.get("/projects", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "projects" in data
    assert "total" in data
    assert data["total"] >= 1
    assert any(p["project_id"] == test_project.project_id for p in data["projects"])


@pytest.mark.asyncio
async def test_list_projects_unauthorized(client: AsyncClient):
    """Test listing projects without authentication."""
    response = await client.get("/projects")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_project(
    client: AsyncClient, auth_headers: dict, test_project: Project
):
    """Test getting a specific project."""
    response = await client.get(
        f"/projects/{test_project.project_id}", headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["project_id"] == test_project.project_id
    assert data["name"] == test_project.name


@pytest.mark.asyncio
async def test_get_project_not_found(client: AsyncClient, auth_headers: dict):
    """Test getting non-existent project."""
    response = await client.get(
        "/projects/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_project(
    client: AsyncClient, auth_headers: dict, test_project: Project
):
    """Test updating a project."""
    response = await client.patch(
        f"/projects/{test_project.project_id}",
        headers=auth_headers,
        json={"name": "Updated Project Name"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Updated Project Name"
    assert data["project_id"] == test_project.project_id


@pytest.mark.asyncio
async def test_update_project_not_found(client: AsyncClient, auth_headers: dict):
    """Test updating non-existent project."""
    response = await client.patch(
        "/projects/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
        json={"name": "New Name"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_project(
    client: AsyncClient, auth_headers: dict, test_project: Project
):
    """Test deleting a project."""
    response = await client.delete(
        f"/projects/{test_project.project_id}", headers=auth_headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify project is deleted
    get_response = await client.get(
        f"/projects/{test_project.project_id}", headers=auth_headers
    )
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_project_not_found(client: AsyncClient, auth_headers: dict):
    """Test deleting non-existent project."""
    response = await client.delete(
        "/projects/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
