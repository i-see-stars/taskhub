# 🚀 TaskHub

[![CI](https://github.com/i-see-stars/taskhub/actions/workflows/ci.yml/badge.svg)](https://github.com/i-see-stars/taskhub/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-93%25-brightgreen.svg)](https://github.com/i-see-stars/taskhub/actions)
[![Python](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/release/python-3140/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791.svg?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**TaskHub** is a modern, high-performance task management platform built with **FastAPI**, **PostgreSQL**, and **SQLAlchemy 2.0**. The project follows **Domain-Driven Design (DDD)** and **Clean Architecture** principles: the codebase is structured into isolated bounded contexts, each with its own domain, application, and infrastructure layers.

---

## Prerequisites

- **Python 3.14+**
- **[uv](https://github.com/astral-sh/uv)** (package manager)
- **Docker** and **Docker Compose** (for PostgreSQL, or full-stack deployment)

---

## Quick Start (Local Development)

The most common workflow: PostgreSQL runs in Docker, the app runs locally with hot-reload.

### 1. Clone and install

```bash
git clone https://github.com/i-see-stars/taskhub.git
cd taskhub
make dev-install
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set a real `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

For local development the defaults work out of the box (DB at `localhost:5432`, user/password `taskhub/taskhub`).

### 3. Start PostgreSQL

```bash
make docker-db
```

This starts only the PostgreSQL container (exposed on port 5432).

### 4. Apply migrations

```bash
make migrate
```

### 5. Run the app

```bash
make run
```

The app starts with hot-reload at:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs (available when `DEBUG=true`)
- ReDoc: http://localhost:8000/redoc (available when `DEBUG=true`)

---

## Running Tests

Tests use a separate database `taskhub_test` to avoid touching dev data.

### 1. Create the test database (once)

Make sure PostgreSQL is running (`make docker-db`), then:

```bash
make docker-db-test
```

### 2. Run tests

```bash
make test          # with coverage report
make test-fast     # without coverage (faster)
```

---

## Full Docker Deployment

Run the entire stack (PostgreSQL + API) in Docker. Useful for production-like environments.

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env: set SECRET_KEY, DEBUG=false, ALLOWED_HOSTS, CORS_ORIGINS
```

### 2. Build and start

```bash
docker compose up -d --build
```

### 3. Apply migrations

Run from the host machine (the DB port is exposed):

```bash
make migrate
```

Or run directly inside the API container:

```bash
docker compose exec api /app/.venv/bin/alembic upgrade head
```

The API is available at http://localhost:8000.

### Production checklist

- [ ] Strong `SECRET_KEY` is configured
- [ ] `DEBUG=false`
- [ ] `ALLOWED_HOSTS` contains only trusted domains
- [ ] `CORS_ORIGINS` contains only trusted origins
- [ ] HTTPS is configured (via reverse proxy like Nginx or Traefik)

---

## Available Make Commands

| Command | Description |
|---|---|
| `make run` | Run dev server with hot-reload |
| `make run-prod` | Run production server locally (no hot-reload) |
| `make test` | Run tests with coverage |
| `make test-fast` | Run tests without coverage |
| `make lint` | Run ruff linter |
| `make format` | Format code with ruff |
| `make type-check` | Run mypy type checking |
| `make check` | Run all checks (lint + type-check + tests) |
| `make ci` | Alias for `make check` |
| `make migrate` | Apply database migrations |
| `make migration MESSAGE="desc"` | Create a new migration |
| `make docker-db` | Start only PostgreSQL in Docker |
| `make docker-db-test` | Create the test database |
| `make docker-up` | Start all services (DB + API) |
| `make docker-down` | Stop all Docker services |
| `make docker-logs` | Tail Docker logs |
| `make docker-build` | Build Docker image |
| `make dev-install` | Install dependencies + pre-commit hooks |
| `make install` | Install production dependencies only |
| `make clean` | Remove cache and temporary files |

---

## Project Structure

```
taskhub/
├── app/
│   ├── shared/                     # Shared kernel (base classes, identifiers, events)
│   ├── identity/                   # Bounded context: authentication & users
│   │   ├── domain/                 # Entities (User, RefreshToken), VOs (Email), repos
│   │   ├── application/            # Use cases (register, login, refresh token)
│   │   └── infrastructure/         # ORM models, JWT, password hashing, routes
│   ├── issue_tracking/             # Bounded context: projects, issues, comments
│   │   ├── domain/                 # Aggregates (Project, Issue), VOs, events, repos
│   │   ├── application/            # Use cases orchestrating domain + event bus
│   │   └── infrastructure/         # ORM models, repositories, queries, routes
│   ├── notifications/              # Bounded context: in-app & email notifications
│   │   ├── domain/                 # Notification entity, repository interface
│   │   ├── application/            # NotificationDispatcher (handles domain events)
│   │   └── infrastructure/         # ORM model, WebSocket manager, routes
│   ├── core/                       # Shared infrastructure (DB engine, config, event bus)
│   └── main.py                     # FastAPI app entry point
├── alembic/                        # Database migrations
├── tests/                          # Test suite (pytest + real DB)
├── Dockerfile                      # Multi-stage production build
├── docker-compose.yml              # PostgreSQL + API services
├── Makefile                        # Development and CI commands
└── pyproject.toml                  # Dependencies and tool configuration
```

---

## Key Features

- **Domain-Driven Design**: Three bounded contexts (identity, issue_tracking, notifications), each fully isolated
- **Clean Architecture**: Domain layer has zero framework dependencies
- **In-process Event Bus**: Bounded contexts communicate via domain events
- **JWT Authentication**: Access + Refresh Token rotation with bcrypt password hashing
- **Project & Issue Management**: Hierarchical tasks (Epic -> Story -> Task -> Bug)
- **Full Async**: Entire stack from API to database (asyncpg)
- **CQRS-lite**: Separated read/write paths for performance
- **WebSocket Notifications**: Real-time push via WebSocket

---

## Security

- Passwords hashed with bcrypt (adaptive salt rounds)
- Short-lived Access Tokens (15 min), long-lived Refresh Tokens (28 days) with one-time use
- TrustedHostMiddleware and CORSMiddleware in production
- Docker containers run as non-root user

---

## License

Distributed under the [MIT](LICENSE) License.
