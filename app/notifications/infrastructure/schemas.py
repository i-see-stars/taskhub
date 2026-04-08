"""Notification Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    """Single notification response."""

    notification_id: str
    issue_id: str
    message: str
    payload: dict[str, object]
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Notification list response."""

    notifications: list[NotificationResponse]
    total: int
