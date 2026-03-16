"""Pytest configuration and fixtures."""

# ruff: noqa: E402
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

# Override settings BEFORE importing app
import app.api.core.config as config_module
from app.api.core.config import Settings

TEST_DATABASE_URL = "postgresql+asyncpg://taskhub:taskhub@localhost:5432/taskhub_test"

# Create test settings and override global settings
_test_settings = Settings(
    DEBUG=True,
    SECRET_KEY=SecretStr("test-secret-key-for-testing-only"),
    ALLOWED_HOSTS=[],
    DATABASE_URL=TEST_DATABASE_URL,
)
config_module.settings = _test_settings

# Now safe to import app and other modules
from app.api.auth.models import User
from app.api.auth.password import get_password_hash
from app.api.core.database import Base, get_session
from app.api.issues.models import Issue, IssuePriority, IssueStatus, IssueType
from app.api.main import app
from app.api.projects.models import Project


@pytest.fixture(scope="session")
async def engine() -> AsyncGenerator[AsyncEngine]:
    """Create a test database engine for the session."""
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,  # Don't reuse connections between tests
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """Create a clean database session for each test."""
    connection = await engine.connect()
    transaction = await connection.begin()

    session = AsyncSession(bind=connection, expire_on_commit=False)

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """Create a test client with database session override."""

    async def override_get_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def auth_headers(client: AsyncClient, test_user: User) -> dict[str, str]:
    """Get authentication headers for test user."""
    response = await client.post(
        "/auth/access-token",
        data={"username": test_user.email, "password": "testpassword123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_project(db_session: AsyncSession, test_user: User) -> Project:
    """Create a test project."""
    project = Project(
        name="Test Project",
        description="A test project",
        key="TEST",
        owner_id=test_user.user_id,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
async def test_issue(
    db_session: AsyncSession, test_user: User, test_project: Project
) -> Issue:
    """Create a test issue."""
    issue = Issue(
        title="Test Issue",
        description="A test issue",
        type=IssueType.TASK,
        status=IssueStatus.TODO,
        priority=IssuePriority.MEDIUM,
        project_id=test_project.project_id,
        reporter_id=test_user.user_id,
    )
    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)
    return issue
