"""Unit tests for issue tracking use cases."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.issue_tracking.application.project_use_cases import (
    AddProjectMemberUseCase,
    CreateProjectUseCase,
    DeleteProjectUseCase,
    RemoveProjectMemberUseCase,
    UpdateMemberRoleUseCase,
    UpdateProjectUseCase,
)
from app.issue_tracking.domain.entities import Project
from app.issue_tracking.domain.exceptions import (
    DuplicateProjectKey,
    InsufficientPermissions,
    LastOwnerCannotBeRemoved,
    MemberNotFound,
    UserAlreadyProjectMember,
)
from app.issue_tracking.domain.value_objects import ProjectRole
from app.shared.domain.identifiers import ProjectId, UserId


def _make_project(
    owner_id: str = "owner-1",
    members: list[tuple[str, ProjectRole]] | None = None,
) -> Project:
    """Create a test project with members.

    Args:
        owner_id: Default owner user ID.
        members: List of (user_id, role) tuples. Defaults to [(owner_id, OWNER)].

    Returns:
        A Project aggregate with the specified members.
    """
    project = Project(
        project_id=ProjectId("proj-1"),
        name="Test",
        key="TEST",
        description=None,
    )
    if members is None:
        members = [(owner_id, ProjectRole.OWNER)]
    for uid, role in members:
        project.add_member(UserId(uid), role)
    return project


def _make_repo(
    project: Project | None = None,
    key_exists: bool = False,
) -> AsyncMock:
    """Create a mocked ProjectRepository.

    Args:
        project: Project to return from get_by_id.
        key_exists: Return value for key_exists check.

    Returns:
        AsyncMock configured as a ProjectRepository.
    """
    repo = AsyncMock()
    if project:
        repo.get_by_id.return_value = project
    repo.key_exists.return_value = key_exists
    repo.save.side_effect = lambda p: p
    return repo


@pytest.mark.asyncio
async def test_create_project_duplicate_key() -> None:
    """Test that creating a project with an existing key raises DuplicateProjectKey."""
    repo = _make_repo(key_exists=True)
    uc = CreateProjectUseCase(project_repo=repo, unit_of_work=AsyncMock())
    with pytest.raises(DuplicateProjectKey):
        await uc.execute("owner-1", "Name", "TEST", None)


@pytest.mark.asyncio
async def test_create_project_success() -> None:
    """Test successful project creation sets caller as OWNER."""
    repo = _make_repo(key_exists=False)
    uow = AsyncMock()
    uc = CreateProjectUseCase(project_repo=repo, unit_of_work=uow)
    await uc.execute("owner-1", "Name", "PROJ", None)
    repo.save.assert_called_once()
    uow.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_project_viewer_raises() -> None:
    """Test that viewers cannot update a project."""
    project = _make_project(
        members=[("owner-1", ProjectRole.OWNER), ("viewer-1", ProjectRole.VIEWER)]
    )
    repo = _make_repo(project=project)
    uc = UpdateProjectUseCase(project_repo=repo, unit_of_work=AsyncMock())
    with pytest.raises(InsufficientPermissions):
        await uc.execute("proj-1", "viewer-1", name="New Name")


@pytest.mark.asyncio
async def test_delete_project_non_owner_raises() -> None:
    """Test that non-owners cannot delete a project."""
    project = _make_project(
        members=[("owner-1", ProjectRole.OWNER), ("member-1", ProjectRole.MEMBER)]
    )
    repo = _make_repo(project=project)
    uc = DeleteProjectUseCase(project_repo=repo, unit_of_work=AsyncMock())
    with pytest.raises(InsufficientPermissions):
        await uc.execute("proj-1", "member-1")


@pytest.mark.asyncio
async def test_add_member_duplicate_raises() -> None:
    """Test that adding an existing member raises UserAlreadyProjectMember."""
    project = _make_project(owner_id="owner-1")
    repo = _make_repo(project=project)
    uc = AddProjectMemberUseCase(project_repo=repo, unit_of_work=AsyncMock())
    with pytest.raises(UserAlreadyProjectMember):
        await uc.execute("proj-1", "owner-1", "owner-1", ProjectRole.MEMBER)


@pytest.mark.asyncio
async def test_add_member_non_owner_raises() -> None:
    """Test that non-owners cannot add members."""
    project = _make_project(
        members=[("owner-1", ProjectRole.OWNER), ("member-1", ProjectRole.MEMBER)]
    )
    repo = _make_repo(project=project)
    uc = AddProjectMemberUseCase(project_repo=repo, unit_of_work=AsyncMock())
    with pytest.raises(InsufficientPermissions):
        await uc.execute("proj-1", "member-1", "new-user", ProjectRole.MEMBER)


@pytest.mark.asyncio
async def test_remove_member_last_owner_raises() -> None:
    """Test that removing the last owner raises LastOwnerCannotBeRemoved."""
    project = _make_project(owner_id="owner-1")
    repo = _make_repo(project=project)
    uc = RemoveProjectMemberUseCase(project_repo=repo, unit_of_work=AsyncMock())
    with pytest.raises(LastOwnerCannotBeRemoved):
        await uc.execute("proj-1", "owner-1", "owner-1")


@pytest.mark.asyncio
async def test_remove_member_not_found_raises() -> None:
    """Test that removing a non-existent member raises MemberNotFound."""
    project = _make_project(owner_id="owner-1")
    repo = _make_repo(project=project)
    uc = RemoveProjectMemberUseCase(project_repo=repo, unit_of_work=AsyncMock())
    with pytest.raises(MemberNotFound):
        await uc.execute("proj-1", "owner-1", "stranger")


@pytest.mark.asyncio
async def test_update_role_demote_last_owner_raises() -> None:
    """Test that demoting the last owner raises LastOwnerCannotBeRemoved."""
    project = _make_project(owner_id="owner-1")
    repo = _make_repo(project=project)
    uc = UpdateMemberRoleUseCase(project_repo=repo, unit_of_work=AsyncMock())
    with pytest.raises(LastOwnerCannotBeRemoved):
        await uc.execute("proj-1", "owner-1", "owner-1", ProjectRole.MEMBER)


@pytest.mark.asyncio
async def test_update_role_not_found_raises() -> None:
    """Test that updating a non-existent member raises MemberNotFound."""
    project = _make_project(owner_id="owner-1")
    repo = _make_repo(project=project)
    uc = UpdateMemberRoleUseCase(project_repo=repo, unit_of_work=AsyncMock())
    with pytest.raises(MemberNotFound):
        await uc.execute("proj-1", "owner-1", "stranger", ProjectRole.MEMBER)
