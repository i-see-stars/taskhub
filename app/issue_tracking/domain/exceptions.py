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


class DuplicateProjectKey(Exception):
    """Raised when creating a project with an existing key."""


class UserAlreadyProjectMember(Exception):
    """Raised when adding a user who is already a project member."""


class LastOwnerCannotBeRemoved(Exception):
    """Raised when trying to demote or remove the last project owner."""


class MemberNotFound(Exception):
    """Raised when a project member cannot be located."""


class CommentNotFound(Exception):
    """Raised when a comment cannot be located."""


class CommentDeleteNotPermitted(Exception):
    """Raised when user lacks permission to delete a comment."""
