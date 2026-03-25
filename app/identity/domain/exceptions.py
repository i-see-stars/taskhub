"""Identity domain exceptions."""


class UserNotFound(Exception):
    """Raised when a user cannot be found by ID or email."""


class InvalidCredentials(Exception):
    """Raised when authentication fails."""


class EmailAlreadyRegistered(Exception):
    """Raised when registering with an already-used email address."""


class InvalidEmail(Exception):
    """Raised when an email address fails format validation."""


class TokenNotFound(Exception):
    """Raised when a refresh token cannot be found."""


class TokenExpired(Exception):
    """Raised when a refresh token has expired."""


class TokenAlreadyUsed(Exception):
    """Raised when a refresh token has already been used."""
