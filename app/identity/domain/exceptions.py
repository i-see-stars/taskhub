"""Identity domain exceptions."""


class UserNotFound(Exception):
    """Raised when a user cannot be found by ID or email."""


class InvalidCredentials(Exception):
    """Raised when authentication fails."""


class EmailAlreadyRegistered(Exception):
    """Raised when registering with an already-used email address."""


class InvalidEmail(Exception):
    """Raised when an email address fails format validation."""
