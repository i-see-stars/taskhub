from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import func, DateTime
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column

from api.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    create_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
