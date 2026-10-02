# HemaNet developer commands. Run `make help` for a list.
# COMPOSE auto-detects Docker Compose v2, falling back to podman-compose.

COMPOSE ?= $(shell if docker compose version >/dev/null 2>&1; then echo "docker compose"; else echo "podman-compose"; fi)

# Local settings (.env is git-ignored; create it with `make env`).
-include .env
POSTGRES_PORT ?= 5432
# Backend tests use a separate, disposable database on the compose Postgres.
TEST_DATABASE_URL ?= postgresql+psycopg://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@127.0.0.1:$(POSTGRES_PORT)/hemanet_test
export TEST_DATABASE_URL

.PHONY: help env install up down logs ps migrate lint format typecheck test audit check

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

env: ## Create .env from .env.example (never overwrites)
	@test -f .env && echo ".env already exists" || (cp .env.example .env && echo "created .env")

install: ## Install backend and frontend dependencies from the lock files
	cd backend && uv sync --locked
	cd frontend && npm ci --no-fund --no-audit

up: ## Build and start the local stack in the background
	$(COMPOSE) up -d --build

down: ## Stop the local stack (keeps the database volume)
	$(COMPOSE) down

logs: ## Follow logs of all services
	$(COMPOSE) logs -f

ps: ## Show service status
	$(COMPOSE) ps

migrate: ## Apply database migrations in the running stack
	$(COMPOSE) run --rm migrate

lint: ## Lint backend (ruff, import-linter) and frontend (eslint)
	cd backend && uv run ruff check .
	cd backend && uv run lint-imports
	cd frontend && npm run lint

format: ## Auto-format backend and frontend
	cd backend && uv run ruff format . && uv run ruff check --fix .
	cd frontend && npm run format

typecheck: ## Type-check backend (mypy strict) and frontend (tsc strict)
	cd backend && uv run mypy
	cd frontend && npm run typecheck

test: ## Run backend tests (needs the compose postgres: `make up`) and frontend tests
	cd backend && uv run pytest
	cd frontend && npm test

audit: ## Security checks: bandit, pip-audit, npm audit
	cd backend && uv run bandit -q -c pyproject.toml -r .
	cd backend && uv export --frozen --no-dev -q | uv run pip-audit --disable-pip -r /dev/stdin
	cd frontend && npm audit --audit-level=high

check: lint typecheck test audit ## Everything CI runs (except secret scan and image builds)
	cd backend && uv run ruff format --check .
	cd frontend && npm run format:check
