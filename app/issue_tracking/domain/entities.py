"""Issue tracking domain entities and aggregates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.issue_tracking.domain.events import IssueAssigned, IssueStatusChanged
from app.issue_tracking.domain.value_objects import (
    IssueStatus,
    IssueType,
    Priority,
    ProjectRole,
)
from app.shared.domain.base import AggregateRoot, Entity
from app.shared.domain.identifiers import CommentId, IssueId, ProjectId, UserId


@dataclass(eq=False)
class Comment(Entity):
    """A comment on an issue. Part of the Issue aggregate."""

    comment_id: CommentId
    issue_id: IssueId
    author_id: UserId
    body: str
    created_at: datetime | None = None


@dataclass(eq=False)
class Issue(AggregateRoot):
    """Issue aggregate root (epic/story/task/bug).

    Enforces: assignee change emits IssueAssigned, status change emits
    IssueStatusChanged.
    """

    issue_id: IssueId
    project_id: ProjectId
    type: IssueType
    title: str
    description: str | None
    status: IssueStatus
    priority: Priority
    assignee_id: UserId | None
    reporter_id: UserId
    parent_id: IssueId | None
    comments: list[Comment] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def assign_to(self, assignee_id: UserId | None) -> None:
        """Assign issue to a user. Emits IssueAssigned if assignee changes.

        Args:
            assignee_id: The new assignee, or None to unassign.
        """
        if assignee_id == self.assignee_id:
            return
        self.assignee_id = assignee_id
        if assignee_id is not None:
            self._events.append(
                IssueAssigned(
                    issue_id=self.issue_id,
                    assignee_id=assignee_id,
                    title=self.title,
                    occurred_at=datetime.now(UTC),
                )
            )

    def change_status(self, new_status: IssueStatus) -> None:
        """Change issue status. Emits IssueStatusChanged if status changes.

        Args:
            new_status: The target status.
        """
        if new_status == self.status:
            return
        old = self.status
        self.status = new_status
        self._events.append(
            IssueStatusChanged(
                issue_id=self.issue_id,
                old_status=old,
                new_status=new_status,
                occurred_at=datetime.now(UTC),
            )
        )

    def add_comment(
        self, comment_id: CommentId, author_id: UserId, body: str
    ) -> Comment:
        """Add a comment to the issue.

        Args:
            comment_id: New comment's identifier.
            author_id: The commenting user.
            body: Comment text.

        Returns:
            The new Comment entity.
        """
        comment = Comment(
            comment_id=comment_id,
            issue_id=self.issue_id,
            author_id=author_id,
            body=body,
        )
        self.comments.append(comment)
        return comment


@dataclass(eq=False)
class ProjectMember(Entity):
    """A user's membership in a project."""

    project_id: ProjectId
    user_id: UserId
    role: ProjectRole
    created_at: datetime | None = None


@dataclass(eq=False)
class Project(AggregateRoot):
    """Project aggregate root -- container for issues."""

    project_id: ProjectId
    name: str
    key: str
    description: str | None
    members: list[ProjectMember] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def add_member(self, user_id: UserId, role: ProjectRole) -> ProjectMember:
        """Add a member to the project.

        Args:
            user_id: The user to add.
            role: The role to assign.

        Returns:
            The new ProjectMember entity.
        """
        member = ProjectMember(project_id=self.project_id, user_id=user_id, role=role)
        self.members.append(member)
        return member

    def get_member(self, user_id: UserId) -> ProjectMember | None:
        """Find a member by user ID.

        Args:
            user_id: The user to look up.

        Returns:
            ProjectMember if found, None otherwise.
        """
        return next((m for m in self.members if m.user_id == user_id), None)
