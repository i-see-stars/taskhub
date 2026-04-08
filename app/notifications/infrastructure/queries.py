"""Read-side query functions for notifications."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.infrastructure.models import NotificationModel


async def list_notifications_for_user(
    session: AsyncSession,
    user_id: str,
    is_read: bool | None = None,
    category: str | None = None,
) -> list[NotificationModel]:
    """List notifications for a user with optional read-status filter.

    Args:
        session: Database session.
        user_id: The user's ID.
        is_read: Optional filter by read status.
        category: Optional JSONB payload category filter.

    Returns:
        List of NotificationModel rows.
    """
    query = select(NotificationModel).where(NotificationModel.user_id == user_id)
    if is_read is not None:
        query = query.where(NotificationModel.is_read == is_read)
    if category is not None:
        query = query.where(NotificationModel.payload.contains({"category": category}))
    query = query.order_by(NotificationModel.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())
