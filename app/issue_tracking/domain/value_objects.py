"""Issue tracking domain value objects."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from app.shared.domain.base import ValueObject

_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]{1,9}$")  # 2-10 chars, uppercase


class IssueType(StrEnum):
    """Classification of an issue."""

    EPIC = "epic"
    STORY = "story"
    TASK = "task"
    BUG = "bug"


class IssueStatus(StrEnum):
    """Current workflow state of an issue."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class Priority(StrEnum):
    """Urgency/importance level."""

    LOWEST = "lowest"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    HIGHEST = "highest"


class ProjectRole(StrEnum):
    """Member's role within a project."""

    OWNER = "owner"
    MEMBER = "member"
    VIEWER = "viewer"


@dataclass(frozen=True)
class ProjectKey(ValueObject):
    """Validated project key string (e.g. 'TASKHUB').

    Rules: uppercase letters and digits, 2-10 characters, must start with a letter.

    Raises:
        ValueError: If the key format is invalid.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate format on construction."""
        if not _KEY_RE.match(self.value):
            raise ValueError(
                f"ProjectKey must match {_KEY_RE.pattern!r}, got {self.value!r}"
            )
