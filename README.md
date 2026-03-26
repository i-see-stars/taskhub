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

## ✨ Key Features

*   🏛️ **Domain-Driven Design**: Three bounded contexts — `identity`, `issue_tracking`, `notifications` — each fully isolated with their own domain models, repositories, and application services.
*   🧅 **Clean Architecture**: Domain layer has zero framework dependencies. Infrastructure (SQLAlchemy, FastAPI) depends on domain, never the other way around.
*   📨 **In-process Event Bus**: Bounded contexts communicate via domain events (`IssueAssigned`, etc.) through a request-scoped event bus — no direct coupling between contexts.
*   🔐 **Secure Authentication**: JWT-based auth with Refresh Token rotation and password hashing using `bcrypt`.
*   📊 **Project & Issue Management**: Hierarchical task structures (Epic -> Story -> Task -> Bug).
*   🚀 **Full Asynchronicity**: The entire stack, from API to database (`asyncpg`), operates asynchronously.
*   🛡️ **Out-of-the-box Security**: Middleware for CORS, Trusted Hosts, and robust data validation via Pydantic v2.
*   ✅ **Code Quality**: 84%+ test coverage, strict static analysis (`mypy`), and modern linting (`ruff`).
*   🐳 **Production-ready**: Optimized multi-stage Docker builds and CI/CD via GitHub Actions.
*   🔄 **Database Migrations**: Async-supported schema management using Alembic.

---

## 🛠 Tech Stack

| Category | Technology |
| :--- | :--- |
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) (Python 3.14+) |
| **Database** | [PostgreSQL 16+](https://www.postgresql.org/) |
| **ORM** | [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async) |
| **Migrations** | [Alembic](https://alembic.sqlalchemy.org/) |
| **Auth** | [PyJWT](https://pyjwt.readthedocs.io/), [bcrypt](https://github.com/pyca/bcrypt/) |
| **Package Manager**| [uv](https://github.com/astral-sh/uv) (Extremely fast) |
| **Validation** | [Pydantic v2](https://docs.pydantic.dev/) |
| **Testing** | [pytest](https://docs.pytest.org/), [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio), [httpx](https://www.python-httpx.org/) |
| **Linting/Formatting**| [Ruff](https://github.com/astral-sh/ruff), [Mypy](http://mypy-lang.org/) |

---

## 🚦 Quick Start

The project uses `uv` for package management and a `Makefile` to automate routine tasks.

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/i-see-stars/taskhub.git
cd taskhub

# Install dependencies (including dev tools)
make dev-install
```

### 2. Configuration
```bash
cp .env.example .env
# Generate a secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Update SECRET_KEY and DATABASE_URL in your .env file
```

### 3. Database & Migrations
```bash
# Start PostgreSQL (if not running locally)
make docker-up

# Apply migrations
make migrate
```

### 4. Run Application
```bash
make run
```
API will be available at: [http://localhost:8000](http://localhost:8000)
Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🏗 Project Architecture

The project follows **Domain-Driven Design** with **Clean Architecture** layering. Each bounded context is self-contained and organized into three layers: domain → application → infrastructure.

```text
taskhub/
├── app/
│   ├── shared/                     # Shared kernel (base classes, identifiers, domain events)
│   │   └── domain/
│   │       ├── base.py             # AggregateRoot, Entity, ValueObject
│   │       ├── events.py           # DomainEvent base class
│   │       └── identifiers.py      # Typed IDs (UserId, IssueId, ...)
│   │
│   ├── identity/                   # Bounded context: authentication & users
│   │   ├── domain/                 # Entities (User, RefreshToken), VOs (Email), repos
│   │   ├── application/            # Use cases (register, login, refresh token)
│   │   └── infrastructure/         # ORM models, JWT, password hashing, routes
│   │
│   ├── issue_tracking/             # Bounded context: projects, issues, comments
│   │   ├── domain/                 # Aggregates (Project, Issue), VOs, domain events, repos
│   │   ├── application/            # App services orchestrating domain + event bus
│   │   └── infrastructure/         # ORM models, repositories, queries, routes
│   │
│   ├── notifications/              # Bounded context: in-app & email notifications
│   │   ├── domain/                 # Notification entity, repository interface
│   │   ├── application/            # NotificationDispatcher (handles domain events)
│   │   └── infrastructure/         # ORM model, WebSocket manager, routes
│   │
│   ├── core/                       # Shared infrastructure (DB engine, config, event bus)
│   └── main.py                     # FastAPI app entry point
│
├── alembic/                        # Database migrations
├── tests/                          # Integration test suite (pytest + real DB)
├── Dockerfile                      # Multi-stage production build
├── Makefile                        # Development and CI commands
└── pyproject.toml                  # Tooling and dependency configuration
```

### Architectural layers

| Layer | Responsibility | Depends on |
| :--- | :--- | :--- |
| **Domain** | Entities, aggregates, value objects, domain events, repository interfaces | Nothing |
| **Application** | Use cases, orchestration, event publishing | Domain only |
| **Infrastructure** | ORM models, DB queries, FastAPI routes, external services | Domain + Application |

### CQRS-lite

Read and write paths are intentionally separated. Writes go through domain aggregates and application services to enforce invariants and emit events. Reads bypass aggregates entirely — they query the database directly via optimized JOIN queries in `infrastructure/queries.py` and return response schemas without loading domain objects. This keeps read endpoints fast without sacrificing domain integrity on writes.

---

## 🧪 Quality & Testing

We maintain high standards of code quality. To run the full suite:

```bash
# Run all checks (Linter, Type-check, Tests)
make check

# Run tests only with coverage report
make test
```

Linting and formatting follow Google-style (docstrings) and PEP8. All commits are verified via `pre-commit` hooks.

---

## 🔒 Security

*   **Passwords**: Never stored in plain text. Hashed using `bcrypt` with adaptive salt rounds.
*   **JWT**: Short-lived Access Tokens (15 min) and long-lived Refresh Tokens (28 days) with one-time use policy (Refresh Token Reuse Detection).
*   **Middleware**:
    *   `TrustedHostMiddleware` — Protects against HTTP Host Header attacks.
    *   `CORSMiddleware` — Strict allowed origins configuration.
*   **Non-root User**: Docker containers run as a non-privileged user for enhanced security.

---

## 📦 Deployment (Production)

For production environments, Docker is recommended:

```bash
# Build and start in background
docker compose up -d --build

# Run migrations inside the container
docker compose exec api uv run alembic upgrade head
```

**Production Checklist:**
- [ ] Strong `SECRET_KEY` is configured.
- [ ] `DEBUG` is set to `false`.
- [ ] `ALLOWED_HOSTS` and `CORS_ORIGINS` contain only trusted domains.
- [ ] HTTPS is configured (e.g., via Nginx or Traefik).

---

## 📜 License

Distributed under the [MIT](LICENSE) License.
