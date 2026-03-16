# 🚀 TaskHub

[![CI](https://github.com/i-see-stars/taskhub/actions/workflows/ci.yml/badge.svg)](https://github.com/i-see-stars/taskhub/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-93%25-brightgreen.svg)](https://github.com/i-see-stars/taskhub/actions)
[![Python](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/release/python-3140/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791.svg?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**TaskHub** is a modern, high-performance task management platform built with **FastAPI**, **PostgreSQL**, and **SQLAlchemy 2.0**. The project is designed with industry best practices: full asynchronicity, strict typing, automated testing, and containerization.

---

## ✨ Key Features

*   🔐 **Secure Authentication**: JWT-based auth with Refresh Token rotation and password hashing using `bcrypt`.
*   📊 **Project & Issue Management**: Hierarchical task structures (Epic -> Story -> Task -> Bug).
*   🚀 **Full Asynchronicity**: The entire stack, from API to database (`asyncpg`), operates asynchronously.
*   🛡️ **Out-of-the-box Security**: Middleware for CORS, Trusted Hosts, and robust data validation via Pydantic v2.
*   ✅ **Code Quality**: 93% test coverage, strict static analysis (`mypy`), and modern linting (`ruff`).
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

Following modular design principles and separation of concerns:

```text
taskhub/
├── alembic/                # Database migrations
├── app/api/
│   ├── auth/               # Authentication module (JWT, passwords, deps)
│   ├── projects/           # Project management module
│   ├── issues/             # Issue module (hierarchy, statuses, types)
│   ├── core/               # Configuration, DB setup, logging
│   └── main.py             # FastAPI application entry point
├── tests/                  # Automated test suite (pytest)
├── pycharm_http_requests/  # HTTP request examples for quick testing
├── Dockerfile              # Multi-stage production build
├── Makefile                # Development and CI commands
└── pyproject.toml          # Tooling and dependency configuration
```

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
