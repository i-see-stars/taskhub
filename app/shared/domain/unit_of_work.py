"""Unit of Work abstraction for transactional consistency."""

from __future__ import annotations

from abc import ABC, abstractmethod


class UnitOfWork(ABC):
    """Abstract Unit of Work — manages transaction boundaries.

    Application services depend on this abstraction instead of
    SQLAlchemy's AsyncSession, keeping the application layer
    free of infrastructure knowledge.
    """

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""

    @abstractmethod
    async def rollback(self) -> None:
        """Roll back the current transaction."""
