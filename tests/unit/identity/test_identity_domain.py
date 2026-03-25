"""Tests for the identity domain layer."""

import pytest

from app.identity.domain.entities import User
from app.identity.domain.exceptions import InvalidEmail
from app.identity.domain.value_objects import Email, NotificationPreferences
from app.shared.domain.identifiers import UserId


def test_email_valid() -> None:
    """Test that valid email addresses are accepted."""
    email = Email(value="user@example.com")
    assert email.value == "user@example.com"


def test_email_invalid_raises() -> None:
    """Test that invalid email addresses raise InvalidEmail."""
    with pytest.raises(InvalidEmail):
        Email(value="not-an-email")


def test_email_missing_domain_raises() -> None:
    """Test that email without domain raises InvalidEmail."""
    with pytest.raises(InvalidEmail):
        Email(value="user@")


def test_notification_preferences_defaults() -> None:
    """Test that notification preferences can be created with values."""
    prefs = NotificationPreferences(notify_in_app=True, notify_email=False)
    assert prefs.notify_in_app is True
    assert prefs.notify_email is False


def test_notification_preferences_immutable() -> None:
    """Test that notification preferences are immutable."""
    prefs = NotificationPreferences(notify_in_app=True, notify_email=True)
    with pytest.raises((AttributeError, TypeError)):
        prefs.notify_in_app = False  # type: ignore[misc]


def test_user_entity_equality() -> None:
    """Test that User equality is determined by ID only."""
    uid = UserId("abc")
    u1 = User(id=uid, email=Email(value="a@b.com"), hashed_password="x")
    u2 = User(id=uid, email=Email(value="c@d.com"), hashed_password="y")
    u3 = User(id=UserId("xyz"), email=Email(value="a@b.com"), hashed_password="x")
    assert u1 == u2  # same id
    assert u1 != u3  # different id


def test_user_default_preferences() -> None:
    """Test that User has correct default notification preferences."""
    user = User(
        id=UserId("1"),
        email=Email(value="test@example.com"),
        hashed_password="hashed",
    )
    assert user.preferences.notify_in_app is True
    assert user.preferences.notify_email is False
