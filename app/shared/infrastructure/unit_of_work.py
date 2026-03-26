"""SQLAlchemy implementation of Unit of Work."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.domain.unit_of_work import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Unit of Work backed by a SQLAlchemy AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a database session.

        Args:
            session: The async database session.
        """
        self._session = session

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Roll back the current transaction."""
        await self._session.rollback()
