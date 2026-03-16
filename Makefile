.PHONY: help install dev-install test lint format type-check pre-commit run docker-build docker-up docker-down migrate migration clean

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	uv sync --frozen --no-dev

dev-install:  ## Install all dependencies including dev tools
	uv sync --frozen
	pre-commit install

test:  ## Run tests with coverage
	uv run pytest --cov=app --cov-report=term-missing --cov-report=html

test-fast:  ## Run tests without coverage
	uv run pytest -v

lint:  ## Run ruff linter
	uv run ruff check .

format:  ## Format code with ruff
	uv run ruff check --fix .
	uv run ruff format .

type-check:  ## Run mypy type checking
	uv run mypy app/ tests/

pre-commit:  ## Run pre-commit on all files
	uv run pre-commit run --all-files

run:  ## Run development server
	uv run fastapi dev app/api/main.py

run-prod:  ## Run production server
	uv run uvicorn app.api.main:app --host 0.0.0.0 --port 8000

docker-build:  ## Build Docker image
	docker build -t taskhub:latest .

docker-up:  ## Start Docker Compose services
	docker compose up -d

docker-down:  ## Stop Docker Compose services
	docker compose down

docker-logs:  ## Show Docker Compose logs
	docker compose logs -f

check:  ## Run all checks (lint, type-check, test)
	uv run ruff check .
	uv run mypy app/ tests/
	uv run pytest

migrate:  ## Run database migrations
	uv run alembic upgrade head

migration:  ## Create a new migration (usage: make migration MESSAGE="your message")
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE is required. Usage: make migration MESSAGE=\"your message\""; \
		exit 1; \
	fi
	uv run alembic revision --autogenerate -m "$(MESSAGE)"

clean:  ## Clean up cache and temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete

ci:  ## Run all CI checks (lint, type-check, test)
	make check
