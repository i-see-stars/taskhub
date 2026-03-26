"""Notification domain exceptions."""


class NotificationNotFound(Exception):
    """Raised when a notification cannot be located."""


class NotificationAccessDenied(Exception):
    """Raised when a user tries to access another user's notification."""
