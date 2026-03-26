"""Issue tracking domain exceptions."""


class ProjectNotFound(Exception):
    """Raised when a project cannot be located."""


class IssueNotFound(Exception):
    """Raised when an issue cannot be located."""


class InsufficientPermissions(Exception):
    """Raised when a viewer attempts a write operation."""


class AssigneeNotProjectMember(Exception):
    """Raised when the assignee is not a member of the project."""


class IssueParentTypeMismatch(Exception):
    """Raised when parent/child issue type hierarchy is violated."""
