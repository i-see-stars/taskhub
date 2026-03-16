# TaskHub Development Guidelines

This document outlines the best practices and standards for development in the TaskHub project. Adhering to these guidelines ensures code consistency, maintainability, and reliability.

## Project Structure & Naming Conventions

### File Naming
- **Routes/Endpoints**: Always name the file containing API endpoints as `routes.py` (e.g., `app/api/auth/routes.py`). Avoid using `views.py`.
- **Dependencies**: Use `deps.py` for FastAPI dependencies (e.g., `app/api/auth/deps.py`).
- **Models**: Database models should be in `models.py`.
- **Schemas**: Pydantic models for request/response validation should be in `schemas.py`.

### Module Structure
Each API module (auth, projects, issues) should follow this structure:
```text
module/
├── __init__.py
├── routes.py    # API endpoints
├── deps.py      # FastAPI dependencies
├── models.py    # SQLAlchemy models
├── schemas.py   # Pydantic models
└── ...          # Other module-specific files (e.g., jwt.py, password.py)
```

## Database & Models

### Base Model
- All database models must inherit from the `Base` class in `app/api/core/database.py`.
- The `Base` class automatically provides `created_at` and `updated_at` columns with automatic timestamping.
- Do not redefine these columns in individual models unless there's a specific reason.

### Migrations
- Always use Alembic for database schema changes.
- Generate migrations using `uv run alembic revision --autogenerate -m "description"`.
- Verify migrations by running `uv run alembic upgrade head`.
- Use descriptive names for migration files.

### Async Support
- Use `AsyncSession` for all database interactions.
- Use `async_sessionmaker` for creating sessions.
- Use `select()`, `scalar()`, `execute()` for SQLAlchemy queries in async context.

## Static Type Hinting (Mypy)

TaskHub uses the strictest possible Mypy configuration.

### Requirements
- **Mandatory Type Annotations**: All functions and methods must have full type annotations, including return types.
- **Strict Mode**: `strict = true` is enabled in `pyproject.toml`.
- **No Untyped Definitions**: `disallow_untyped_defs = true` and `disallow_incomplete_defs = true` are enforced.
- **Async Generators**: For async generator functions (like database session providers or test fixtures), use `AsyncGenerator[YieldType, None]` as the return type.

### CI Enforcement
- Type checking is enforced in CI for both `app/` and `tests/` directories.
- Run locally with `uv run mypy app/ tests/` or `make check`.

## Linting & Formatting (Ruff)

### Standards
- **Line Length**: 88 characters.
- **Target Version**: Python 3.14.
- **Formatting**: Handled automatically by Ruff. Do not use `--unsafe-fixes`.

### Rules
- `I` (isort): For import sorting.
- `D` (pydocstyle): For docstring validation.
- `UP` (pyupgrade): For modern Python syntax.
- `B` (flake8-bugbear): For common bugs and design issues.

## Documentation (Docstrings)

### Convention
- Use **Google Style** for all docstrings.
- Docstrings are required for all modules, classes, and public functions.

### Example
```python
def example_function(param1: str, param2: int) -> bool:
    """Do something useful.

    Args:
        param1: The first parameter.
        param2: The second parameter.

    Returns:
        True if successful, False otherwise.
    """
    ...
```

## Testing

### Reliability
- Use Pydantic models to validate API responses in tests for better reliability.
- Instead of checking dictionaries, use `model_validate(response.json())`.

### Example Test
```python
@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    """Test user registration."""
    response = await client.post(
        "/auth/register",
        json={"email": "newuser@example.com", "password": "securepass123"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = UserResponse.model_validate(response.json())
    assert data.email == "newuser@example.com"
    assert data.user_id is not None
```

### Coverage
- Maintain high test coverage (currently ~93%).
- Run tests with `make test` or `uv run pytest tests/`.

## Development Workflow

- **Check before commit**: Run `make check` to execute linting, type checking, and tests in one go.
- **CI**: The CI pipeline runs on pushes and pull requests to the `main` branch.
- **Production Readiness**: Follow the checklist in `README.md` for production deployments.
