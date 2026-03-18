# CLAUDE.md — TaskHub Project Guide

## Project Overview

TaskHub is a task management platform built with FastAPI, PostgreSQL, and modern Python tooling.

**Stack:** FastAPI, SQLAlchemy 2.0+, asyncpg, Pydantic 2.5+, PostgreSQL 16, Alembic, pytest
**Package manager:** uv
**Deployment:** Docker Compose

## Quick Reference

```bash
make dev-install    # Install dependencies + pre-commit hooks
make run            # Run development server
make test           # Run tests with coverage
make test-fast      # Run tests without coverage
make lint           # Run ruff linter
make format         # Format code with ruff
make type-check     # Run mypy type checking
make migrate        # Apply database migrations
make migration MESSAGE="desc"  # Create new migration
make ci             # Run all CI checks
make docker-up      # Start Docker services
make clean          # Clean cache files
```

---

## Workflow Orchestration

### 1. Plan First Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately — don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes — don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests — then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

---

## Python Development Rules

### Code Style & Standards

- **PEP 8** with type hints everywhere (FastAPI and Pydantic rely on them)
- **Ruff** for linting and formatting (line length: 88, double quotes, target: Python 3.14)
- Use `pytest` + `pytest-asyncio` for async tests
- All functions/methods/classes must have English docstrings (Google style)
- Do not use `--unsafe-fixes` with Ruff
- **Never import inside functions or methods.** All imports must be at the top of the module. The only exception is `if TYPE_CHECKING:` blocks for avoiding circular imports.

### SOLID Principles

Apply SOLID at every layer of the codebase:

- **SRP (Single Responsibility):** Each class/function has one reason to change.
  - `password.py` handles hashing only; `jwt.py` handles tokens only; routes handle HTTP only.
  - If a route handler is doing DB queries AND business logic AND auth checks, split it.
- **OCP (Open/Closed):** Extend behavior via new classes, not by modifying existing code. Add new features by creating new modules/classes, not adding `if/else` blocks.
- **LSP (Liskov Substitution):** Subclasses must be substitutable for their base classes without breaking functionality.
- **ISP (Interface Segregation):** Keep interfaces lean. Don't force clients to depend on methods they don't use.
- **DIP (Dependency Inversion):** Depend on abstractions, not concretions. Use dependency injection.

### GoF Design Patterns

Use these patterns where they naturally improve the code. Don't force them.

#### Creational
- **Factory Method**: Use `async_sessionmaker` as the session factory — never instantiate `AsyncSession` directly. Centralize object creation behind a factory rather than scattering `__init__` calls.
- **Singleton**: `settings = Settings()` in `config.py` is treated as a singleton by convention — a single shared instance, not re-instantiated elsewhere. Note: Python module variables don't enforce true Singleton; this relies on discipline.
- **Builder**: Construct complex objects step by step. A good example is building a SQLAlchemy query incrementally based on optional filters rather than assembling one monolithic expression:
  ```python
  query = select(Project)
  if filters.status:
      query = query.where(Project.status == filters.status)
  if filters.owner_id:
      query = query.where(Project.owner_id == filters.owner_id)
  if filters.limit:
      query = query.limit(filters.limit)
  ```

#### Structural
- **Facade**: A service layer (`services.py`) acts as a facade over data access and external systems. Routes call services; services handle the complexity underneath.
- **Adapter**: Converts an incompatible interface into one a client expects. Use when integrating external systems or libraries whose interfaces don't match your domain.
- **Decorator**: Wraps a function or object to add behavior without modifying it. In Python, implement as a higher-order function:
  ```python
  def with_logging(func):
      @functools.wraps(func)
      async def wrapper(*args, **kwargs):
          logger.info(f"Calling {func.__name__}")
          return await func(*args, **kwargs)
      return wrapper
  ```
  Note: `@router.get` is a Python language construct that registers routes — it is not the GoF Decorator pattern.

#### Behavioral
- **Strategy**: Define a family of interchangeable algorithms and inject the appropriate one rather than branching with `if/else`.
- **Template Method**: Define a fixed algorithm skeleton in a base class, deferring specific steps to subclasses. Apply only when a true base class with an invariant algorithm exists — don't conflate with general refactoring.
- **Chain of Responsibility**: Pass a request along a chain of handlers, each deciding to process or forward it. FastAPI middleware follows this spirit, though technically it is closer to Pipe & Filter since `call_next` always forwards unless an exception is raised.
- **Observer**: Define a one-to-many dependency so that when one object changes state, all dependents are notified. Prefer for domain events to keep routes thin and free of side-effect calls.

### Configuration Management

**NEVER use hardcoded configuration values.** All tunable values (timeouts, limits, lengths, TTLs, thresholds, feature flags) must come from configuration — never module-level constants, `os.getenv()` calls, or magic numbers.

```python
# CORRECT — using Pydantic Settings
from api.core.config import settings
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.db_pool_size
)
code = secrets.token_urlsafe(settings.linking_code_length)

# WRONG — hardcoded constant
LINKING_CODE_LENGTH = 32
code = secrets.token_urlsafe(LINKING_CODE_LENGTH)

# WRONG — raw os.getenv
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://...")
engine = create_async_engine(DATABASE_URL, pool_size=10)
```

**Configuration structure:**
- All config in `app/api/core/config.py` using Pydantic Settings
- Environment variables loaded from `.env`
- Use `SecretStr` for sensitive values (passwords, API keys, tokens)
- Provide sensible defaults for dev, require explicit values for production

### HTTP Status Codes

Always use FastAPI's `status` module, never hardcode integers:

```python
# CORRECT
from fastapi import status
raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="...")
assert response.status_code == status.HTTP_404_NOT_FOUND

# WRONG — hardcoded status codes
raise HTTPException(status_code=400, detail="...")
assert response.status_code == 404
```

### Docstrings

Use **Google style** exclusively. Required for all modules, classes, and public functions.

```python
# CORRECT
def process_task(task_id: int) -> dict[str, object]:
    """Process a task by ID.

    Args:
        task_id: The ID of the task to process.

    Returns:
        Dictionary with processing result.

    Raises:
        ValueError: If task_id is invalid.
        TaskNotFoundError: If task doesn't exist.
    """
    ...

# WRONG — no docstring, wrong style, or non-English
```

### Type Hints

TaskHub uses **strict mypy**. All code must satisfy it.

- Every function and method must have full type annotations including return types.
- For async generators (e.g., session providers, test fixtures), use `AsyncGenerator[YieldType, None]` as return type.
- Never use `Any` unless absolutely unavoidable and justified with a comment.
- `strict = true` is enforced in `pyproject.toml` — run `make type-check` before committing.

### Database Migrations

1. Change models in `app/api/*/models.py`
2. `make migration MESSAGE="description"`
3. Review generated script in `alembic/versions/`
4. Test migration: `make migrate`
5. Test rollback: `uv run alembic downgrade -1`
6. Commit migration file with code changes

**Never skip migration review.** Always check:
- Are indexes created where needed?
- Are constraints properly named?
- Is data migration safe for production?
- Can migration be rolled back?

### Testing

- All new functionality must have tests
- Never hit real infrastructure in unit tests — use mocks/fixtures
- Tests live in `tests/` directory
- Use `pytest` fixtures for setup/teardown
- Use `pytest.mark` for categorizing tests (slow, integration, unit)
- Maintain >80% code coverage (currently ~93% — don't regress)
- Use `AsyncGenerator[YieldType, None]` for async fixture return types
- **Validate responses with Pydantic**, not raw dicts:

```python
# CORRECT — validates shape and types
data = UserResponse.model_validate(response.json())
assert data.email == "user@example.com"

# WRONG — fragile, no type safety
assert response.json()["email"] == "user@example.com"
```

Test structure:
```python
@pytest.mark.asyncio
async def test_feature_name(client: AsyncClient) -> None:
    """Test that feature does X when Y."""
    # Arrange
    setup_data()

    # Act
    response = await client.post("/endpoint", json={...})

    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    data = ResponseSchema.model_validate(response.json())
    assert data.field == expected_value
```

### Import Organization

```python
# Standard library
import os
from typing import AsyncGenerator

# Third-party
from fastapi import FastAPI, Depends
from sqlalchemy import select

# Local application
from app.api.core.config import settings
from app.api.auth.models import User
```

### Error Handling

- Use specific exception types
- Always provide meaningful error messages
- Log errors with context
- Return appropriate HTTP status codes
- Don't expose internal errors to API responses
- Centralize error message strings in `api_messages.py` per module

```python
# CORRECT
try:
    user = await get_user(user_id)
except UserNotFoundError:
    logger.warning("User not found", extra={"user_id": user_id})
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found",
    )

# WRONG
try:
    user = await get_user(user_id)
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

---

## Architecture Guidelines

### Project Structure

```
taskhub/
├── app/
│   └── api/
│       ├── auth/              # Authentication (JWT, bcrypt, refresh tokens)
│       ├── projects/          # Project management
│       ├── issues/            # Issue tracking (Epic → Story → Task → Bug)
│       ├── core/              # Config, database, logging
│       └── main.py            # FastAPI app, middleware, router registration
├── alembic/                   # Database migrations
├── tests/                     # Test suite
└── tasks/                     # Project management (todo.md, lessons.md)
```

### Module Organization

Each feature module **must** follow this exact structure:

```
module/
├── __init__.py
├── routes.py        # FastAPI endpoints — use routes.py, NOT views.py
├── deps.py          # FastAPI dependencies — use deps.py, NOT dependencies.py
├── models.py        # SQLAlchemy ORM models
├── schemas.py       # Pydantic request/response schemas
└── services.py      # Business logic (add when routes grow complex)
```

File naming is **non-negotiable**: `routes.py` and `deps.py` are the project standards.

### Base Model

All SQLAlchemy models must inherit from `Base` in `app/api/core/database.py`.

- `Base` automatically provides `created_at` and `updated_at` with server-side defaults.
- Do not redefine these columns in individual models.
- Use SQLAlchemy 2.0 `Mapped[T]` type annotation style.

### Separation of Concerns

| Layer | File | Responsibility |
|---|---|---|
| Routes | `routes.py` | HTTP request/response, auth checks, call services/DB |
| Schemas | `schemas.py` | Pydantic validation and serialization only |
| Models | `models.py` | Database schema only, no business logic |
| Services | `services.py` | Business logic, orchestration (add when needed) |
| Dependencies | `deps.py` | Reusable `Depends()` functions |
| Core | `core/` | Config, DB engine, logging — infrastructure only |

---

## Security Best Practices

- Never commit secrets (use `.env`, add to `.gitignore`)
- Use `SECRET_KEY` for JWT and cryptographic operations
- Hash passwords with bcrypt via `passlib` (configurable rounds via settings)
- Mitigate timing attacks: perform dummy hash check on nonexistent users
- Validate all user input with Pydantic — never trust raw request data
- Use parameterized queries (SQLAlchemy handles this automatically)
- Refresh tokens are single-use — track `used` flag in DB
- Set appropriate CORS origins in production via settings
- Configure `ALLOWED_HOSTS` for production
- Enable HTTPS in production
- Keep dependencies updated (`uv lock --upgrade`)

---

## Git Workflow

- Branch from `main` for new features
- Use descriptive branch names: `feature/user-auth`, `fix/login-bug`
- Commit messages: imperative mood, descriptive
- Run `make ci` before committing (linting + type-check + tests)
- Use pre-commit hooks (auto-installed via `make dev-install`)
- Squash commits before merging to main (optional)

---

_This file is the single source of truth for AI assistants working on TaskHub. Follow these guidelines strictly._
