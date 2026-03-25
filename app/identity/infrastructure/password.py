"""Password hashing and verification."""

import bcrypt

from app.api.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash.

    Args:
        plain_password: The plain text password to verify.
        hashed_password: The hash to verify against.

    Returns:
        True if the password matches, False otherwise.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """Generate a bcrypt hash for the given password.

    Args:
        password: The plain text password to hash.

    Returns:
        The hashed password as a string.
    """
    return bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt(settings.password_bcrypt_rounds),
    ).decode()


DUMMY_PASSWORD = get_password_hash("")
