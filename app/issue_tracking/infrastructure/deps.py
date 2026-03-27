"""Issue tracking FastAPI dependencies."""

from __future__ import annotations

from typing import cast

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.event_bus import EventBus, EventHandler
from app.identity.infrastructure.models import UserModel
from app.issue_tracking.application.services import IssueAppService, ProjectAppService
from app.issue_tracking.domain.events import IssueAssigned
from app.issue_tracking.infrastructure.repositories import (
    PostgresIssueRepository,
    PostgresProjectRepository,
)
from app.notifications.application.dispatcher import (
    NotificationContext,
    NotificationDispatcher,
)
from app.notifications.infrastructure.connection_manager import ConnectionManager
from app.shared.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def get_connection_manager(request: Request) -> ConnectionManager:
    """Get WebSocket connection manager from app state.

    Args:
        request: The FastAPI request.

    Returns:
        The application's ConnectionManager instance.
    """
    return cast(ConnectionManager, request.app.state.connection_manager)


def get_event_bus(
    session: AsyncSession = Depends(get_session),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
) -> EventBus:
    """Create request-scoped event bus with notification handler subscribed.

    Args:
        session: The request-scoped database session.
        connection_manager: The WebSocket connection manager.

    Returns:
        Configured EventBus instance.
    """
    bus = EventBus()
    dispatcher = NotificationDispatcher(
        session=session, connection_manager=connection_manager
    )

    async def handle_issue_assigned(event: IssueAssigned) -> None:
        """Handle IssueAssigned event by dispatching notifications."""
        result = await session.execute(
            select(UserModel).where(UserModel.user_id == event.assignee_id.value)
        )
        assignee = result.scalar_one_or_none()
        if assignee and event.assignee_id.value:
            ctx = NotificationContext(
                recipient_id=event.assignee_id.value,
                issue_id=event.issue_id.value,
                message=f"You were assigned to issue: {event.title}",
            )
            await dispatcher.dispatch(
                ctx,
                notify_in_app=assignee.notify_in_app,
                notify_email=assignee.notify_email,
            )

    bus.subscribe(IssueAssigned, cast(EventHandler, handle_issue_assigned))
    return bus


def get_issue_app_service(
    session: AsyncSession = Depends(get_session),
    event_bus: EventBus = Depends(get_event_bus),
) -> IssueAppService:
    """Create request-scoped IssueAppService.

    Args:
        session: Database session.
        event_bus: Event bus with handlers subscribed.

    Returns:
        Configured IssueAppService.
    """
    return IssueAppService(
        issue_repo=PostgresIssueRepository(session),
        project_repo=PostgresProjectRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
        event_bus=event_bus,
    )


def get_project_app_service(
    session: AsyncSession = Depends(get_session),
) -> ProjectAppService:
    """Create request-scoped ProjectAppService.

    Args:
        session: Database session.

    Returns:
        Configured ProjectAppService.
    """
    return ProjectAppService(
        project_repo=PostgresProjectRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )
