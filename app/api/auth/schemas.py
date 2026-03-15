"""Auth Pydantic schemas."""

from pydantic import BaseModel, ConfigDict, EmailStr


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str


class UserUpdatePasswordRequest(BaseModel):
    """User password update request schema."""

    password: str


class UserCreateRequest(BaseModel):
    """User creation request schema."""

    email: EmailStr
    password: str


class AccessTokenResponse(BaseModel):
    """Access token response schema."""

    token_type: str = "bearer"
    access_token: str
    expires_at: int
    refresh_token: str
    refresh_token_expires_at: int

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """User response schema."""

    user_id: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)
