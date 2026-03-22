"""Issue business logic service."""

import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.models import User
from app.api.issues.models import Issue
from app.api.issues.schemas import IssueUpdate
from app.api.notifications.services import NotificationContext, NotificationDispatcher
from app.api.projects.models import Project, ProjectMember, ProjectMemberRole

logger = logging.getLogger(__name__)


class IssueService:
    """Service for issue business logic.

    Handles issue updates and triggers notifications when assignee changes.
    """

    def __init__(
        self, session: AsyncSession, dispatcher: NotificationDispatcher
    ) -> None:
        """Initialize with database session and notification dispatcher.

        Args:
            session: The async database session.
            dispatcher: The notification dispatcher.
        """
        self.session = session
        self.dispatcher = dispatcher

    async def update_issue(
        self,
        issue_id: str,
        issue_data: IssueUpdate,
        current_user: User,
    ) -> Issue:
        """Update an issue and trigger notification if assignee changes.

        Args:
            issue_id: The issue UUID.
            issue_data: The update data.
            current_user: The authenticated user.

        Returns:
            The updated issue.

        Raises:
            HTTPException: 404 if not found, 403 if viewer, 400 if invalid assignee.
        """
        # Load issue with membership check (matches existing route query pattern)
        result = await self.session.execute(
            select(Issue)
            .join(Project, Issue.project_id == Project.project_id)
            .join(
                ProjectMember,
                (ProjectMember.project_id == Project.project_id)
                & (ProjectMember.user_id == current_user.user_id),
            )
            .where(Issue.issue_id == issue_id)
        )
        issue = result.scalar_one_or_none()
        if not issue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Issue not found",
            )

        # Check role
        member_result = await self.session.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == issue.project_id,
                ProjectMember.user_id == current_user.user_id,
            )
        )
        member = member_result.scalar_one_or_none()
        if member and member.role == ProjectMemberRole.VIEWER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Viewers cannot modify issues",
            )

        update_data = issue_data.model_dump(exclude_unset=True)

        # Validate assignee if being changed
        if "assignee_id" in update_data and update_data["assignee_id"] is not None:
            assignee_member = await self.session.execute(
                select(ProjectMember).where(
                    ProjectMember.project_id == issue.project_id,
                    ProjectMember.user_id == update_data["assignee_id"],
                )
            )
            if not assignee_member.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assignee must be a member of the project",
                )

        # Capture old assignee before update
        old_assignee_id = issue.assignee_id

        # Apply updates
        for field, value in update_data.items():
            setattr(issue, field, value)

        # Trigger notification if assignee changed (before commit for atomicity)
        new_assignee_id = issue.assignee_id
        if (
            new_assignee_id
            and new_assignee_id != old_assignee_id
            and new_assignee_id != current_user.user_id
        ):
            assignee_result = await self.session.execute(
                select(User).where(User.user_id == new_assignee_id)
            )
            assignee = assignee_result.scalar_one_or_none()
            if assignee:
                context = NotificationContext(
                    recipient_id=new_assignee_id,
                    issue_id=issue.issue_id,
                    message=f"You were assigned to issue: {issue.title}",
                )
                await self.dispatcher.dispatch(
                    context,
                    notify_in_app=assignee.notify_in_app,
                    notify_email=assignee.notify_email,
                )

        # Single commit for both issue update and notification (atomic)
        await self.session.commit()
        await self.session.refresh(issue)

        return issue
