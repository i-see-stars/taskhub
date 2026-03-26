"""Issue tracking API routes (projects + issues)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.identity.infrastructure.deps import get_current_user
from app.identity.infrastructure.models import UserModel
from app.issue_tracking.application.services import IssueAppService
from app.issue_tracking.domain.exceptions import (
    AssigneeNotProjectMember,
    InsufficientPermissions,
    IssueNotFound,
)
from app.issue_tracking.domain.value_objects import ProjectRole
from app.issue_tracking.infrastructure.deps import get_issue_app_service
from app.issue_tracking.infrastructure.models import (
    IssueModel,
    ProjectMemberModel,
    ProjectModel,
)
from app.issue_tracking.infrastructure.queries import (
    list_issues_for_user,
    list_projects_for_user,
)
from app.issue_tracking.infrastructure.schemas import (
    IssueCreate,
    IssueListResponse,
    IssueResponse,
    IssueUpdate,
    ProjectCreate,
    ProjectListResponse,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectMembersListResponse,
    ProjectMemberUpdate,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter()


# ---- Helper functions ----


async def _get_project_and_member(
    project_id: str,
    session: AsyncSession,
    current_user: UserModel,
) -> tuple[ProjectModel, ProjectMemberModel]:
    """Get project and verify user membership.

    Args:
        project_id: The project UUID.
        session: Database session.
        current_user: The authenticated user.

    Returns:
        Tuple of (ProjectModel, ProjectMemberModel).

    Raises:
        HTTPException: 404 if project not found, 403 if user is not a member.
    """
    project_result = await session.execute(
        select(ProjectModel).where(ProjectModel.project_id == project_id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    member_result = await session.execute(
        select(ProjectMemberModel).where(
            ProjectMemberModel.project_id == project_id,
            ProjectMemberModel.user_id == current_user.user_id,
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return project, member


async def _require_project_member(
    project_id: str,
    session: AsyncSession,
    current_user: UserModel,
) -> ProjectMemberModel:
    """Verify the current user is a member of the given project.

    Args:
        project_id: The project UUID.
        session: Database session.
        current_user: The authenticated user.

    Returns:
        The user's ProjectMemberModel record.

    Raises:
        HTTPException: 404 if project not found, 403 if user is not a member.
    """
    project_result = await session.execute(
        select(ProjectModel).where(ProjectModel.project_id == project_id)
    )
    if not project_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    member_result = await session.execute(
        select(ProjectMemberModel).where(
            ProjectMemberModel.project_id == project_id,
            ProjectMemberModel.user_id == current_user.user_id,
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return member


async def _validate_assignee(
    assignee_id: str,
    project_id: str,
    session: AsyncSession,
) -> None:
    """Validate that the assignee is a member of the project.

    Args:
        assignee_id: The user ID to assign.
        project_id: The project UUID.
        session: Database session.

    Raises:
        HTTPException: 400 if assignee is not a project member.
    """
    member_result = await session.execute(
        select(ProjectMemberModel).where(
            ProjectMemberModel.project_id == project_id,
            ProjectMemberModel.user_id == assignee_id,
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee must be a member of the project",
        )


# ---- Project endpoints ----


@router.get("/projects", response_model=ProjectListResponse, tags=["projects"])
async def list_projects(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ProjectListResponse:
    """List all projects the current user is a member of."""
    projects = await list_projects_for_user(session, current_user.user_id)
    return ProjectListResponse(projects=projects, total=len(projects))


@router.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["projects"],
)
async def create_project(
    project_data: ProjectCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ProjectModel:
    """Create a new project and add creator as owner."""
    existing = await session.execute(
        select(ProjectModel).where(ProjectModel.key == project_data.key)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project with this key already exists",
        )

    project = ProjectModel(**project_data.model_dump())
    session.add(project)
    await session.flush()

    member = ProjectMemberModel(
        project_id=project.project_id,
        user_id=current_user.user_id,
        role=ProjectRole.OWNER,
    )
    session.add(member)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("/projects/{project_id}", response_model=ProjectResponse, tags=["projects"])
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ProjectModel:
    """Get project by ID."""
    project, _ = await _get_project_and_member(project_id, session, current_user)
    return project


@router.patch(
    "/projects/{project_id}", response_model=ProjectResponse, tags=["projects"]
)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ProjectModel:
    """Update project. Requires member or owner role."""
    project, member = await _get_project_and_member(project_id, session, current_user)

    if member.role == ProjectRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot modify projects",
        )

    for field, value in project_data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    await session.commit()
    await session.refresh(project)
    return project


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["projects"],
)
async def delete_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    """Delete project. Requires owner role."""
    project, member = await _get_project_and_member(project_id, session, current_user)

    if member.role != ProjectRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can delete it",
        )

    await session.delete(project)
    await session.commit()


# ---- Member endpoints ----


@router.get(
    "/projects/{project_id}/members",
    response_model=ProjectMembersListResponse,
    tags=["projects"],
)
async def list_members(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ProjectMembersListResponse:
    """List all members of a project."""
    await _get_project_and_member(project_id, session, current_user)

    result = await session.execute(
        select(ProjectMemberModel).where(ProjectMemberModel.project_id == project_id)
    )
    members = result.scalars().all()
    return ProjectMembersListResponse(members=list(members), total=len(members))


@router.post(
    "/projects/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["projects"],
)
async def add_member(
    project_id: str,
    member_data: ProjectMemberCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ProjectMemberModel:
    """Add a member to the project. Requires owner role."""
    _, member = await _get_project_and_member(project_id, session, current_user)

    if member.role != ProjectRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can add members",
        )

    # Check target user exists
    user_result = await session.execute(
        select(UserModel).where(UserModel.user_id == member_data.user_id)
    )
    if not user_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check not already a member
    existing = await session.execute(
        select(ProjectMemberModel).where(
            ProjectMemberModel.project_id == project_id,
            ProjectMemberModel.user_id == member_data.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this project",
        )

    new_member = ProjectMemberModel(
        project_id=project_id,
        user_id=member_data.user_id,
        role=member_data.role,
    )
    session.add(new_member)
    await session.commit()
    await session.refresh(new_member)
    return new_member


@router.patch(
    "/projects/{project_id}/members/{user_id}",
    response_model=ProjectMemberResponse,
    tags=["projects"],
)
async def update_member_role(
    project_id: str,
    user_id: str,
    member_data: ProjectMemberUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ProjectMemberModel:
    """Update a member's role. Requires owner role."""
    _, current_member = await _get_project_and_member(project_id, session, current_user)

    if current_member.role != ProjectRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can change roles",
        )

    target_result = await session.execute(
        select(ProjectMemberModel).where(
            ProjectMemberModel.project_id == project_id,
            ProjectMemberModel.user_id == user_id,
        )
    )
    target_member = target_result.scalar_one_or_none()
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    if (
        target_member.role == ProjectRole.OWNER
        and member_data.role != ProjectRole.OWNER
    ):
        owners_result = await session.execute(
            select(ProjectMemberModel).where(
                ProjectMemberModel.project_id == project_id,
                ProjectMemberModel.role == ProjectRole.OWNER,
            )
        )
        if len(owners_result.scalars().all()) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last owner",
            )

    target_member.role = member_data.role
    await session.commit()
    await session.refresh(target_member)
    return target_member


@router.delete(
    "/projects/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["projects"],
)
async def remove_member(
    project_id: str,
    user_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    """Remove a member from the project. Requires owner role."""
    _, current_member = await _get_project_and_member(project_id, session, current_user)

    if current_member.role != ProjectRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can remove members",
        )

    target_result = await session.execute(
        select(ProjectMemberModel).where(
            ProjectMemberModel.project_id == project_id,
            ProjectMemberModel.user_id == user_id,
        )
    )
    target_member = target_result.scalar_one_or_none()
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    if target_member.role == ProjectRole.OWNER:
        owners_result = await session.execute(
            select(ProjectMemberModel).where(
                ProjectMemberModel.project_id == project_id,
                ProjectMemberModel.role == ProjectRole.OWNER,
            )
        )
        if len(owners_result.scalars().all()) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner",
            )

    await session.delete(target_member)
    await session.commit()


# ---- Issue endpoints ----


@router.get("/issues", response_model=IssueListResponse, tags=["issues"])
async def list_issues(
    project_id: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> IssueListResponse:
    """List all issues accessible to current user."""
    issues = await list_issues_for_user(session, current_user.user_id, project_id)
    return IssueListResponse(issues=issues, total=len(issues))


@router.post(
    "/issues",
    response_model=IssueResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["issues"],
)
async def create_issue(
    issue_data: IssueCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> IssueModel:
    """Create a new issue."""
    member = await _require_project_member(issue_data.project_id, session, current_user)

    if member.role == ProjectRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot create issues",
        )

    if issue_data.parent_id:
        parent_result = await session.execute(
            select(IssueModel).where(
                IssueModel.issue_id == issue_data.parent_id,
                IssueModel.project_id == issue_data.project_id,
            )
        )
        if not parent_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent issue not found",
            )

    if issue_data.assignee_id:
        await _validate_assignee(issue_data.assignee_id, issue_data.project_id, session)

    issue = IssueModel(
        **issue_data.model_dump(),
        reporter_id=current_user.user_id,
    )
    session.add(issue)
    await session.commit()
    await session.refresh(issue)
    return issue


@router.get("/issues/{issue_id}", response_model=IssueResponse, tags=["issues"])
async def get_issue(
    issue_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> IssueModel:
    """Get issue by ID."""
    result = await session.execute(
        select(IssueModel)
        .join(ProjectModel, IssueModel.project_id == ProjectModel.project_id)
        .join(
            ProjectMemberModel,
            (ProjectMemberModel.project_id == ProjectModel.project_id)
            & (ProjectMemberModel.user_id == current_user.user_id),
        )
        .where(IssueModel.issue_id == issue_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )
    return issue


@router.patch("/issues/{issue_id}", response_model=IssueResponse, tags=["issues"])
async def update_issue(
    issue_id: str,
    issue_data: IssueUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
    service: IssueAppService = Depends(get_issue_app_service),
) -> IssueModel:
    """Update issue. Uses IssueAppService for domain logic and event bus."""
    update_fields = issue_data.model_dump(exclude_unset=True)
    try:
        await service.update_issue(
            issue_id=issue_id,
            requesting_user_id=current_user.user_id,
            **update_fields,
        )
    except IssueNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found"
        ) from None
    except InsufficientPermissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot modify issues",
        ) from None
    except AssigneeNotProjectMember:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee must be a member of the project",
        ) from None

    # Reload ORM model for response serialization
    result = await session.execute(
        select(IssueModel).where(IssueModel.issue_id == issue_id)
    )
    return result.scalar_one()


@router.delete(
    "/issues/{issue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["issues"],
)
async def delete_issue(
    issue_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    """Delete issue. Requires member or owner role."""
    result = await session.execute(
        select(IssueModel)
        .join(ProjectModel, IssueModel.project_id == ProjectModel.project_id)
        .join(
            ProjectMemberModel,
            (ProjectMemberModel.project_id == ProjectModel.project_id)
            & (ProjectMemberModel.user_id == current_user.user_id),
        )
        .where(IssueModel.issue_id == issue_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    member_result = await session.execute(
        select(ProjectMemberModel).where(
            ProjectMemberModel.project_id == issue.project_id,
            ProjectMemberModel.user_id == current_user.user_id,
        )
    )
    member = member_result.scalar_one_or_none()
    if member and member.role == ProjectRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot delete issues",
        )

    await session.delete(issue)
    await session.commit()
