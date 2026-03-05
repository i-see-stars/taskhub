from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "TaskHub"
    DATABASE_URL: str
    DEBUG: bool = False

    jwt_issuer: str = "taskhub"
    jwt_secret_key: SecretStr = SecretStr(
        "9f3e0e9c8c7f4b7a8c9d1e2f3a4b5c6d7e8f9a0b1c2d3e4f"
    )
    jwt_access_token_expire_secs: int = 15 * 60  # 15 minutes
    jwt_refresh_token_expire_secs: int = 28 * 24 * 3600  # 28 days
    jwt_algorithm: str = "HS256"

    # Password hashing
    password_bcrypt_rounds: int = 12

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown environment variables
    )


settings = Settings()
