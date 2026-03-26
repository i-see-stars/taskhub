"""Issue tracking domain events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.issue_tracking.domain.value_objects import IssueStatus
from app.shared.domain.events import DomainEvent
from app.shared.domain.identifiers import IssueId, ProjectId, UserId


@dataclass(frozen=True)
class IssueAssigned(DomainEvent):
    """Emitted when an issue is assigned to a user."""

    issue_id: IssueId
    assignee_id: UserId
    title: str
    occurred_at: datetime


@dataclass(frozen=True)
class IssueStatusChanged(DomainEvent):
    """Emitted when an issue status changes."""

    issue_id: IssueId
    old_status: IssueStatus
    new_status: IssueStatus
    occurred_at: datetime


@dataclass(frozen=True)
class IssueCreated(DomainEvent):
    """Emitted when a new issue is created."""

    issue_id: IssueId
    project_id: ProjectId
    type: str
    reporter_id: UserId
    occurred_at: datetime
