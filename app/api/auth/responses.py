"""Auth response schemas."""

from pydantic import BaseModel, ConfigDict, EmailStr


class BaseResponse(BaseModel):
    """Base response schema."""

    model_config = ConfigDict(from_attributes=True)


class AccessTokenResponse(BaseResponse):
    """Access token response schema."""

    token_type: str = "Bearer"
    access_token: str
    expires_at: int
    refresh_token: str
    refresh_token_expires_at: int


class UserResponse(BaseResponse):
    """User response schema."""

    user_id: str
    email: EmailStr
