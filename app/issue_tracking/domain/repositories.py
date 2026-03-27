"""Issue tracking domain repository interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.issue_tracking.domain.entities import Issue, Project


class ProjectRepository(ABC):
    """Abstract repository for Project aggregate."""

    @abstractmethod
    async def get_by_id(self, project_id: object) -> Project:
        """Fetch project with members. Raises ProjectNotFound if absent."""

    @abstractmethod
    async def save(self, project: Project) -> Project:
        """Persist new or updated project."""

    @abstractmethod
    async def list_for_user(self, user_id: object) -> list[Project]:
        """List all projects the given user is a member of."""

    @abstractmethod
    async def delete(self, project_id: object) -> None:
        """Delete project by ID."""

    @abstractmethod
    async def key_exists(self, key: str) -> bool:
        """Check if a project with this key already exists.

        Args:
            key: The project key to check.

        Returns:
            True if a project with this key exists.
        """


class IssueRepository(ABC):
    """Abstract repository for Issue aggregate."""

    @abstractmethod
    async def get_by_id(self, issue_id: object) -> Issue:
        """Fetch issue (without comments by default). Raises IssueNotFound if absent."""

    @abstractmethod
    async def get_with_comments(self, issue_id: object) -> Issue:
        """Fetch issue with its comments loaded. Raises IssueNotFound if absent."""

    @abstractmethod
    async def save(self, issue: Issue) -> Issue:
        """Persist new or updated issue, syncing comments."""

    @abstractmethod
    async def delete(self, issue_id: object) -> None:
        """Delete issue by ID."""
