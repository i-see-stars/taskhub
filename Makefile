.PHONY: help
help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install:  ## Install production dependencies
	uv sync --frozen --no-dev

.PHONY: dev-install
dev-install:  ## Install all dependencies including dev tools
	uv sync --frozen
	pre-commit install

.PHONY: test
test:  ## Run tests with coverage
	uv run pytest --cov=app --cov-report=term-missing --cov-report=html

.PHONY: test-fast
test-fast:  ## Run tests without coverage
	uv run pytest -v

.PHONY: lint
lint:  ## Run ruff linter
	uv run ruff check .

.PHONY: format
format:  ## Format code with ruff
	uv run ruff check --fix .
	uv run ruff format .

.PHONY: type-check
type-check:  ## Run mypy type checking
	uv run mypy app/ tests/

.PHONY: pre-commit
pre-commit:  ## Run pre-commit on all files
	uv run pre-commit run --all-files

.PHONY: run
run:  ## Run development server (requires DB running)
	uv run fastapi dev app/main.py

.PHONY: run-prod
run-prod:  ## Run production server locally (requires DB running)
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

.PHONY: docker-db
docker-db:  ## Start only PostgreSQL in Docker
	docker compose up -d db

.PHONY: docker-db-test
docker-db-test:  ## Create test database (run after docker-db)
	docker compose exec db psql -U taskhub -c "CREATE DATABASE taskhub_test;" 2>/dev/null || true

.PHONY: docker-build
docker-build:  ## Build Docker image
	docker build -t taskhub:latest .

.PHONY: docker-up
docker-up:  ## Start all Docker Compose services (DB + API)
	docker compose up -d

.PHONY: docker-up-build
docker-up-build:  ## Rebuild image and start all Docker Compose services
	docker compose up -d --build

.PHONY: docker-down
docker-down:  ## Stop Docker Compose services
	docker compose down

.PHONY: docker-logs
docker-logs:  ## Show Docker Compose logs
	docker compose logs -f

.PHONY: check
check:  ## Run all checks (lint, type-check, test)
	uv run ruff check .
	uv run mypy app/ tests/
	uv run pytest

.PHONY: migrate
migrate:  ## Run database migrations
	uv run alembic upgrade head

.PHONY: migration
migration:  ## Create a new migration (usage: make migration MESSAGE="your message")
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE is required. Usage: make migration MESSAGE=\"your message\""; \
		exit 1; \
	fi
	uv run alembic revision --autogenerate -m "$(MESSAGE)"

.PHONY: clean
clean:  ## Clean up cache and temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete

.PHONY: ci
ci:  ## Run all CI checks (lint, type-check, test)
	make check
