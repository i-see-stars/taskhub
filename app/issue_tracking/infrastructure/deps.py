"""Issue tracking FastAPI dependencies."""

from __future__ import annotations

from typing import cast

from fastapi import Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.event_bus import EventBus, EventHandler
from app.identity.infrastructure.deps import get_current_user
from app.identity.infrastructure.models import UserModel
from app.issue_tracking.application.issue_use_cases import (
    CreateCommentUseCase,
    CreateIssueUseCase,
    DeleteCommentUseCase,
    DeleteIssueUseCase,
    UpdateIssueUseCase,
)
from app.issue_tracking.application.project_use_cases import (
    AddProjectMemberUseCase,
    CreateProjectUseCase,
    DeleteProjectUseCase,
    RemoveProjectMemberUseCase,
    UpdateMemberRoleUseCase,
    UpdateProjectUseCase,
)
from app.issue_tracking.domain.events import IssueAssigned
from app.issue_tracking.infrastructure.models import (
    CommentModel,
    IssueModel,
    ProjectMemberModel,
    ProjectModel,
)
from app.issue_tracking.infrastructure.queries import (
    get_issue_by_id,
    get_project_by_id,
    list_comments_for_issue,
    list_issues_for_user,
    list_members_for_project,
    list_projects_for_user,
)
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


# ---- Project use case factories ----


def get_create_project_use_case(
    session: AsyncSession = Depends(get_session),
) -> CreateProjectUseCase:
    """Create CreateProjectUseCase.

    Args:
        session: The request-scoped database session.

    Returns:
        Configured CreateProjectUseCase instance.
    """
    return CreateProjectUseCase(
        project_repo=PostgresProjectRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


def get_update_project_use_case(
    session: AsyncSession = Depends(get_session),
) -> UpdateProjectUseCase:
    """Create UpdateProjectUseCase.

    Args:
        session: The request-scoped database session.

    Returns:
        Configured UpdateProjectUseCase instance.
    """
    return UpdateProjectUseCase(
        project_repo=PostgresProjectRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


def get_delete_project_use_case(
    session: AsyncSession = Depends(get_session),
) -> DeleteProjectUseCase:
    """Create DeleteProjectUseCase.

    Args:
        session: The request-scoped database session.

    Returns:
        Configured DeleteProjectUseCase instance.
    """
    return DeleteProjectUseCase(
        project_repo=PostgresProjectRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


def get_add_project_member_use_case(
    session: AsyncSession = Depends(get_session),
) -> AddProjectMemberUseCase:
    """Create AddProjectMemberUseCase.

    Args:
        session: The request-scoped database session.

    Returns:
        Configured AddProjectMemberUseCase instance.
    """
    return AddProjectMemberUseCase(
        project_repo=PostgresProjectRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


def get_remove_project_member_use_case(
    session: AsyncSession = Depends(get_session),
) -> RemoveProjectMemberUseCase:
    """Create RemoveProjectMemberUseCase.

    Args:
        session: The request-scoped database session.

    Returns:
        Configured RemoveProjectMemberUseCase instance.
    """
    return RemoveProjectMemberUseCase(
        project_repo=PostgresProjectRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


def get_update_member_role_use_case(
    session: AsyncSession = Depends(get_session),
) -> UpdateMemberRoleUseCase:
    """Create UpdateMemberRoleUseCase.

    Args:
        session: The request-scoped database session.

    Returns:
        Configured UpdateMemberRoleUseCase instance.
    """
    return UpdateMemberRoleUseCase(
        project_repo=PostgresProjectRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


# ---- Issue use case factories ----


def get_create_issue_use_case(
    session: AsyncSession = Depends(get_session),
) -> CreateIssueUseCase:
    """Create CreateIssueUseCase.

    Args:
        session: The request-scoped database session.

    Returns:
        Configured CreateIssueUseCase instance.
    """
    return CreateIssueUseCase(
        issue_repo=PostgresIssueRepository(session),
        project_repo=PostgresProjectRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


def get_update_issue_use_case(
    session: AsyncSession = Depends(get_session),
    event_bus: EventBus = Depends(get_event_bus),
) -> UpdateIssueUseCase:
    """Create UpdateIssueUseCase with event bus.

    Args:
        session: The request-scoped database session.
        event_bus: Configured event bus with notification handler.

    Returns:
        Configured UpdateIssueUseCase instance.
    """
    return UpdateIssueUseCase(
        issue_repo=PostgresIssueRepository(session),
        project_repo=PostgresProjectRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
        event_bus=event_bus,
    )


def get_delete_issue_use_case(
    session: AsyncSession = Depends(get_session),
) -> DeleteIssueUseCase:
    """Create DeleteIssueUseCase.

    Args:
        session: The request-scoped database session.

    Returns:
        Configured DeleteIssueUseCase instance.
    """
    return DeleteIssueUseCase(
        issue_repo=PostgresIssueRepository(session),
        project_repo=PostgresProjectRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


def get_create_comment_use_case(
    session: AsyncSession = Depends(get_session),
) -> CreateCommentUseCase:
    """Create CreateCommentUseCase.

    Args:
        session: The request-scoped database session.

    Returns:
        Configured CreateCommentUseCase instance.
    """
    return CreateCommentUseCase(
        issue_repo=PostgresIssueRepository(session),
        project_repo=PostgresProjectRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


def get_delete_comment_use_case(
    session: AsyncSession = Depends(get_session),
) -> DeleteCommentUseCase:
    """Create DeleteCommentUseCase.

    Args:
        session: The request-scoped database session.

    Returns:
        Configured DeleteCommentUseCase instance.
    """
    return DeleteCommentUseCase(
        issue_repo=PostgresIssueRepository(session),
        project_repo=PostgresProjectRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


# ---- Read-side query dependencies ----


async def resolve_project_list(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[ProjectModel]:
    """Resolve project list for current user.

    Args:
        session: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        List of ProjectModel rows the user is a member of.
    """
    return await list_projects_for_user(session, current_user.user_id)


async def resolve_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ProjectModel:
    """Resolve a single project by ID with access check.

    Args:
        project_id: The project UUID from the path.
        session: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The ProjectModel if found and accessible.

    Raises:
        HTTPException: 404 if project not found or user has no access.
    """
    project = await get_project_by_id(session, project_id, current_user.user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


async def resolve_project_members(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[ProjectMemberModel]:
    """Resolve member list for a project with access check.

    Args:
        project_id: The project UUID from the path.
        session: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        List of ProjectMemberModel for the project.

    Raises:
        HTTPException: 404 if project not found or user has no access.
    """
    members = await list_members_for_project(session, project_id, current_user.user_id)
    if members is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return members


async def resolve_issue_list(
    project_id: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[IssueModel]:
    """Resolve issue list for current user.

    Args:
        project_id: Optional project filter from query param.
        session: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        List of IssueModel rows accessible to the user.
    """
    return await list_issues_for_user(session, current_user.user_id, project_id)


async def resolve_issue(
    issue_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> IssueModel:
    """Resolve a single issue by ID with access check.

    Args:
        issue_id: The issue UUID from the path.
        session: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The IssueModel if found and accessible.

    Raises:
        HTTPException: 404 if issue not found or user has no access.
    """
    issue = await get_issue_by_id(session, issue_id, current_user.user_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )
    return issue


async def resolve_comment_list(
    issue_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[CommentModel]:
    """Resolve comment list for an issue with access check.

    Args:
        issue_id: The issue UUID from the path.
        session: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        List of CommentModel for the issue.

    Raises:
        HTTPException: 404 if issue not found or user has no access.
    """
    comments = await list_comments_for_issue(session, issue_id, current_user.user_id)
    if comments is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )
    return comments
