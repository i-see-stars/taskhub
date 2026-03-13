from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    PROJECT_NAME: str = "TaskHub"
    DATABASE_URL: str
    DEBUG: bool = False

    # Security
    SECRET_KEY: SecretStr  # Required for production
    ALLOWED_HOSTS: list[str] = ["*"]  # Override in production
    CORS_ORIGINS: list[str] = []  # Override in production

    # JWT
    jwt_issuer: str = "taskhub"
    jwt_secret_key: SecretStr | None = None  # Deprecated, use SECRET_KEY
    jwt_access_token_expire_secs: int = 15 * 60  # 15 minutes
    jwt_refresh_token_expire_secs: int = 28 * 24 * 3600  # 28 days
    jwt_algorithm: str = "HS256"

    # Password hashing
    password_bcrypt_rounds: int = 12

    def get_jwt_secret(self) -> str:
        """Get JWT secret from SECRET_KEY or fallback to jwt_secret_key."""
        if self.jwt_secret_key:
            return self.jwt_secret_key.get_secret_value()
        return self.SECRET_KEY.get_secret_value()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown environment variables
    )


settings = Settings()
