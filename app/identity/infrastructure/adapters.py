"""Identity infrastructure adapters — concrete implementations of application ports."""

from __future__ import annotations

from app.identity.application.ports import AccessToken, PasswordHasher, TokenService
from app.identity.infrastructure.jwt import create_jwt_token
from app.identity.infrastructure.password import (
    DUMMY_PASSWORD,
    get_password_hash,
    verify_password,
)


class BcryptPasswordHasher(PasswordHasher):
    """PasswordHasher backed by bcrypt."""

    def hash(self, password: str) -> str:
        """Hash a plaintext password using bcrypt.

        Args:
            password: Plaintext password.

        Returns:
            Hashed password string.
        """
        return get_password_hash(password)

    def verify(self, password: str, hashed: str) -> bool:
        """Verify a plaintext password against a bcrypt hash.

        Args:
            password: Plaintext password.
            hashed: Hashed password.

        Returns:
            True if match.
        """
        return verify_password(password, hashed)

    def dummy_verify(self) -> None:
        """Run dummy hash check for timing-attack mitigation."""
        verify_password("dummy", DUMMY_PASSWORD)


class JWTTokenService(TokenService):
    """TokenService backed by PyJWT."""

    def create_access_token(self, user_id: str) -> AccessToken:
        """Create a JWT access token.

        Args:
            user_id: The user's ID.

        Returns:
            AccessToken with token string and expiry.
        """
        jwt_token = create_jwt_token(user_id)
        return AccessToken(
            token=jwt_token.access_token,
            expires_at=jwt_token.payload.exp,
        )
