"""Project write use cases.

Each use case is a single-purpose class with one execute() method.
Depends on domain abstractions only (Repository, UnitOfWork).
"""

from __future__ import annotations

from app.issue_tracking.domain.entities import Project, ProjectMember
from app.issue_tracking.domain.exceptions import (
    DuplicateProjectKey,
    InsufficientPermissions,
    LastOwnerCannotBeRemoved,
    MemberNotFound,
    UserAlreadyProjectMember,
)
from app.issue_tracking.domain.repositories import ProjectRepository
from app.issue_tracking.domain.value_objects import ProjectRole
from app.shared.domain.identifiers import ProjectId, UserId
from app.shared.domain.unit_of_work import UnitOfWork


class CreateProjectUseCase:
    """Create a new project and set creator as owner."""

    def __init__(
        self, project_repo: ProjectRepository, unit_of_work: UnitOfWork
    ) -> None:
        """Initialize.

        Args:
            project_repo: Abstract project repository.
            unit_of_work: Unit of work for transaction management.
        """
        self._repo = project_repo
        self._unit_of_work = unit_of_work

    async def execute(
        self, owner_id: str, name: str, key: str, description: str | None
    ) -> Project:
        """Create project.

        Args:
            owner_id: The creating user's ID.
            name: Project display name.
            key: Unique project key (e.g. 'TASKHUB').
            description: Optional description.

        Returns:
            Created Project aggregate.

        Raises:
            DuplicateProjectKey: If key already exists.
        """
        if await self._repo.key_exists(key):
            raise DuplicateProjectKey(key)
        project = Project(
            project_id=ProjectId(""),
            name=name,
            key=key,
            description=description,
        )
        project.add_member(UserId(owner_id), ProjectRole.OWNER)
        saved = await self._repo.save(project)
        await self._unit_of_work.commit()
        return saved


class UpdateProjectUseCase:
    """Update project fields. Viewers cannot update."""

    def __init__(
        self, project_repo: ProjectRepository, unit_of_work: UnitOfWork
    ) -> None:
        """Initialize.

        Args:
            project_repo: Abstract project repository.
            unit_of_work: Unit of work for transaction management.
        """
        self._repo = project_repo
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        project_id: str,
        requesting_user_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> Project:
        """Update project.

        Args:
            project_id: The project UUID.
            requesting_user_id: The user performing the update.
            name: New name (optional).
            description: New description (optional).

        Returns:
            Updated Project aggregate.

        Raises:
            ProjectNotFound: If project doesn't exist.
            InsufficientPermissions: If user is VIEWER or not a member.
        """
        project = await self._repo.get_by_id(ProjectId(project_id))
        member = project.get_member(UserId(requesting_user_id))
        if not member:
            raise InsufficientPermissions("User is not a project member")
        if member.role == ProjectRole.VIEWER:
            raise InsufficientPermissions("Viewers cannot modify projects")
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        saved = await self._repo.save(project)
        await self._unit_of_work.commit()
        return saved


class DeleteProjectUseCase:
    """Delete a project. Requester must be OWNER."""

    def __init__(
        self, project_repo: ProjectRepository, unit_of_work: UnitOfWork
    ) -> None:
        """Initialize.

        Args:
            project_repo: Abstract project repository.
            unit_of_work: Unit of work for transaction management.
        """
        self._repo = project_repo
        self._unit_of_work = unit_of_work

    async def execute(self, project_id: str, requesting_user_id: str) -> None:
        """Delete project.

        Args:
            project_id: The project UUID.
            requesting_user_id: The user performing the deletion.

        Raises:
            ProjectNotFound: If project doesn't exist.
            InsufficientPermissions: If requester is not OWNER.
        """
        project = await self._repo.get_by_id(ProjectId(project_id))
        member = project.get_member(UserId(requesting_user_id))
        if not member or member.role != ProjectRole.OWNER:
            raise InsufficientPermissions("Only owners can delete a project")
        await self._repo.delete(ProjectId(project_id))
        await self._unit_of_work.commit()


class AddProjectMemberUseCase:
    """Add a member to a project. Requester must be OWNER."""

    def __init__(
        self, project_repo: ProjectRepository, unit_of_work: UnitOfWork
    ) -> None:
        """Initialize.

        Args:
            project_repo: Abstract project repository.
            unit_of_work: Unit of work for transaction management.
        """
        self._repo = project_repo
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        project_id: str,
        requesting_user_id: str,
        target_user_id: str,
        role: ProjectRole,
    ) -> ProjectMember:
        """Add member. Returns the newly added ProjectMember.

        Args:
            project_id: The project UUID.
            requesting_user_id: Must be OWNER.
            target_user_id: The user to add.
            role: The role to assign.

        Returns:
            The newly added ProjectMember with timestamps populated.

        Raises:
            ProjectNotFound: If project doesn't exist.
            InsufficientPermissions: If requester is not OWNER.
            UserAlreadyProjectMember: If user is already a member.
        """
        project = await self._repo.get_by_id(ProjectId(project_id))
        requester = project.get_member(UserId(requesting_user_id))
        if not requester or requester.role != ProjectRole.OWNER:
            raise InsufficientPermissions("Only owners can add members")
        if project.get_member(UserId(target_user_id)):
            raise UserAlreadyProjectMember(target_user_id)
        member = project.add_member(UserId(target_user_id), role)
        saved_project = await self._repo.save(project)
        await self._unit_of_work.commit()
        # Return the member from the saved project (has created_at populated)
        saved_member = saved_project.get_member(UserId(target_user_id))
        return saved_member if saved_member is not None else member


class RemoveProjectMemberUseCase:
    """Remove a member from a project. Requester must be OWNER."""

    def __init__(
        self, project_repo: ProjectRepository, unit_of_work: UnitOfWork
    ) -> None:
        """Initialize.

        Args:
            project_repo: Abstract project repository.
            unit_of_work: Unit of work for transaction management.
        """
        self._repo = project_repo
        self._unit_of_work = unit_of_work

    async def execute(
        self, project_id: str, requesting_user_id: str, target_user_id: str
    ) -> None:
        """Remove member.

        Args:
            project_id: The project UUID.
            requesting_user_id: Must be OWNER.
            target_user_id: The user to remove.

        Raises:
            ProjectNotFound: If project doesn't exist.
            InsufficientPermissions: If requester is not OWNER.
            MemberNotFound: If target is not a member.
            LastOwnerCannotBeRemoved: If removing the last owner.
        """
        project = await self._repo.get_by_id(ProjectId(project_id))
        requester = project.get_member(UserId(requesting_user_id))
        if not requester or requester.role != ProjectRole.OWNER:
            raise InsufficientPermissions("Only owners can remove members")
        target = project.get_member(UserId(target_user_id))
        if not target:
            raise MemberNotFound(f"Member {target_user_id!r} not found")
        if target.role == ProjectRole.OWNER:
            owners = [m for m in project.members if m.role == ProjectRole.OWNER]
            if len(owners) <= 1:
                raise LastOwnerCannotBeRemoved("Cannot remove the last owner")
        project.members = [
            m for m in project.members if m.user_id != UserId(target_user_id)
        ]
        await self._repo.save(project)
        await self._unit_of_work.commit()


class UpdateMemberRoleUseCase:
    """Update a member's role. Requester must be OWNER."""

    def __init__(
        self, project_repo: ProjectRepository, unit_of_work: UnitOfWork
    ) -> None:
        """Initialize.

        Args:
            project_repo: Abstract project repository.
            unit_of_work: Unit of work for transaction management.
        """
        self._repo = project_repo
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        project_id: str,
        requesting_user_id: str,
        target_user_id: str,
        new_role: ProjectRole,
    ) -> ProjectMember:
        """Update role. Returns the updated ProjectMember.

        Args:
            project_id: The project UUID.
            requesting_user_id: Must be OWNER.
            target_user_id: The user whose role changes.
            new_role: The new role to assign.

        Returns:
            The updated ProjectMember with timestamps populated.

        Raises:
            ProjectNotFound: If project doesn't exist.
            InsufficientPermissions: If requester is not OWNER.
            MemberNotFound: If target is not a member.
            LastOwnerCannotBeRemoved: If demoting the last owner.
        """
        project = await self._repo.get_by_id(ProjectId(project_id))
        requester = project.get_member(UserId(requesting_user_id))
        if not requester or requester.role != ProjectRole.OWNER:
            raise InsufficientPermissions("Only owners can change roles")
        target = project.get_member(UserId(target_user_id))
        if not target:
            raise MemberNotFound(f"Member {target_user_id!r} not found")
        if target.role == ProjectRole.OWNER and new_role != ProjectRole.OWNER:
            owners = [m for m in project.members if m.role == ProjectRole.OWNER]
            if len(owners) <= 1:
                raise LastOwnerCannotBeRemoved("Cannot demote the last owner")
        target.role = new_role
        saved_project = await self._repo.save(project)
        await self._unit_of_work.commit()
        saved_member = saved_project.get_member(UserId(target_user_id))
        return saved_member if saved_member is not None else target
