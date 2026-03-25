"""Tests for the issue_tracking domain layer."""

import pytest

from app.issue_tracking.domain.entities import Issue
from app.issue_tracking.domain.events import IssueAssigned, IssueStatusChanged
from app.issue_tracking.domain.value_objects import (
    IssueStatus,
    IssueType,
    Priority,
    ProjectKey,
)
from app.shared.domain.identifiers import IssueId, ProjectId, UserId


def _make_issue(assignee_id: UserId | None = None) -> Issue:
    """Create a test Issue with sensible defaults.

    Args:
        assignee_id: Optional assignee for the issue.

    Returns:
        A new Issue instance.
    """
    return Issue(
        issue_id=IssueId("issue-1"),
        project_id=ProjectId("proj-1"),
        type=IssueType.TASK,
        title="Test issue",
        description=None,
        status=IssueStatus.TODO,
        priority=Priority.MEDIUM,
        assignee_id=assignee_id,
        reporter_id=UserId("user-reporter"),
        parent_id=None,
    )


def test_assign_to_emits_issue_assigned_event() -> None:
    """Test that assigning an issue emits an IssueAssigned event."""
    issue = _make_issue()
    new_assignee = UserId("user-2")
    issue.assign_to(new_assignee)

    events = issue.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], IssueAssigned)
    assert events[0].issue_id == issue.issue_id
    assert events[0].assignee_id == new_assignee
    assert events[0].title == "Test issue"


def test_assign_to_same_user_no_event() -> None:
    """Test that re-assigning to the same user emits no event."""
    issue = _make_issue(assignee_id=UserId("user-2"))
    issue.assign_to(UserId("user-2"))  # same assignee
    assert issue.pull_events() == []


def test_change_status_emits_event() -> None:
    """Test that changing status emits an IssueStatusChanged event."""
    issue = _make_issue()
    issue.change_status(IssueStatus.IN_PROGRESS)

    events = issue.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], IssueStatusChanged)
    assert events[0].old_status == IssueStatus.TODO
    assert events[0].new_status == IssueStatus.IN_PROGRESS


def test_project_key_valid() -> None:
    """Test that a valid project key is accepted."""
    key = ProjectKey(value="MYPROJ")
    assert key.value == "MYPROJ"


def test_project_key_invalid_lowercase() -> None:
    """Test that a lowercase project key is rejected."""
    with pytest.raises(ValueError, match="ProjectKey"):
        ProjectKey(value="myproj")


def test_project_key_too_short() -> None:
    """Test that a single-character project key is rejected."""
    with pytest.raises(ValueError, match="ProjectKey"):
        ProjectKey(value="A")  # min 2 chars
