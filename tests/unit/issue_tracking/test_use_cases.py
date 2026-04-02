"""Unit tests for issue tracking use cases."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.issue_tracking.application.issue_use_cases import (
    CreateCommentUseCase,
    DeleteCommentUseCase,
    DeleteIssueUseCase,
)
from app.issue_tracking.application.project_use_cases import (
    AddProjectMemberUseCase,
    CreateProjectUseCase,
    DeleteProjectUseCase,
    RemoveProjectMemberUseCase,
    UpdateMemberRoleUseCase,
    UpdateProjectUseCase,
)
from app.issue_tracking.domain.entities import Comment, Issue, Project
from app.issue_tracking.domain.exceptions import (
    CommentDeleteNotPermitted,
    CommentNotFound,
    DuplicateProjectKey,
    InsufficientPermissions,
    LastOwnerCannotBeRemoved,
    MemberNotFound,
    UserAlreadyProjectMember,
)
from app.issue_tracking.domain.value_objects import (
    IssueStatus,
    IssueType,
    Priority,
    ProjectRole,
)
from app.shared.domain.identifiers import CommentId, IssueId, ProjectId, UserId


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


def _make_issue(
    project_id: str = "proj-1",
    reporter_id: str = "user-1",
    comments: list[Comment] | None = None,
) -> Issue:
    """Create a test issue.

    Args:
        project_id: The issue's project ID.
        reporter_id: The reporter's user ID.
        comments: Optional list of comments.

    Returns:
        An Issue aggregate.
    """
    issue = Issue(
        issue_id=IssueId("issue-1"),
        project_id=ProjectId(project_id),
        type=IssueType.TASK,
        title="Test issue",
        description=None,
        status=IssueStatus.TODO,
        priority=Priority.MEDIUM,
        reporter_id=UserId(reporter_id),
        assignee_id=None,
        parent_id=None,
    )
    issue.comments = comments or []
    return issue


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


@pytest.mark.asyncio
async def test_delete_issue_viewer_raises() -> None:
    """Test that viewers cannot delete issues."""
    project = _make_project(
        members=[("owner-1", ProjectRole.OWNER), ("viewer-1", ProjectRole.VIEWER)]
    )
    issue = _make_issue(project_id="proj-1")
    issue_repo = AsyncMock()
    issue_repo.get_by_id.return_value = issue
    project_repo = AsyncMock()
    project_repo.get_by_id.return_value = project

    uc = DeleteIssueUseCase(
        issue_repo=issue_repo,
        project_repo=project_repo,
        unit_of_work=AsyncMock(),
    )
    with pytest.raises(InsufficientPermissions):
        await uc.execute("issue-1", "viewer-1")


@pytest.mark.asyncio
async def test_delete_comment_wrong_author_raises() -> None:
    """Test that non-author non-owner cannot delete a comment."""
    comment = Comment(
        comment_id=CommentId("cmt-1"),
        issue_id=IssueId("issue-1"),
        author_id=UserId("author-1"),
        body="Hello",
        created_at=None,
    )
    project = _make_project(
        members=[("owner-1", ProjectRole.OWNER), ("other-1", ProjectRole.MEMBER)]
    )
    issue = _make_issue(comments=[comment])
    issue_repo = AsyncMock()
    issue_repo.get_with_comments.return_value = issue
    project_repo = AsyncMock()
    project_repo.get_by_id.return_value = project

    uc = DeleteCommentUseCase(
        issue_repo=issue_repo,
        project_repo=project_repo,
        unit_of_work=AsyncMock(),
    )
    with pytest.raises(CommentDeleteNotPermitted):
        await uc.execute("issue-1", "cmt-1", "other-1")


@pytest.mark.asyncio
async def test_delete_comment_not_found_raises() -> None:
    """Test that deleting a non-existent comment raises CommentNotFound."""
    project = _make_project(owner_id="owner-1")
    issue = _make_issue(comments=[])
    issue_repo = AsyncMock()
    issue_repo.get_with_comments.return_value = issue
    project_repo = AsyncMock()
    project_repo.get_by_id.return_value = project

    uc = DeleteCommentUseCase(
        issue_repo=issue_repo,
        project_repo=project_repo,
        unit_of_work=AsyncMock(),
    )
    with pytest.raises(CommentNotFound):
        await uc.execute("issue-1", "cmt-999", "owner-1")


@pytest.mark.asyncio
async def test_create_comment_viewer_raises() -> None:
    """Test that viewers cannot add comments."""
    project = _make_project(
        members=[("owner-1", ProjectRole.OWNER), ("viewer-1", ProjectRole.VIEWER)]
    )
    issue = _make_issue(project_id="proj-1")
    issue_repo = AsyncMock()
    issue_repo.get_with_comments.return_value = issue
    project_repo = AsyncMock()
    project_repo.get_by_id.return_value = project
    issue_repo.save.side_effect = lambda i: i

    uc = CreateCommentUseCase(
        issue_repo=issue_repo,
        project_repo=project_repo,
        unit_of_work=AsyncMock(),
    )
    with pytest.raises(InsufficientPermissions):
        await uc.execute("issue-1", "viewer-1", "My comment")
