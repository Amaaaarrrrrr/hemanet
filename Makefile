# HemaNet developer commands. Run `make help` for a list.
# COMPOSE auto-detects Docker Compose v2, falling back to podman-compose.

COMPOSE ?= $(shell if docker compose version >/dev/null 2>&1; then echo "docker compose"; else echo "podman-compose"; fi)

.PHONY: help env up down logs ps lint format typecheck test audit check

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

env: ## Create .env from .env.example (never overwrites)
	@test -f .env && echo ".env already exists" || (cp .env.example .env && echo "created .env")

up: ## Build and start the local stack in the background
	$(COMPOSE) up -d --build

down: ## Stop the local stack (keeps the database volume)
	$(COMPOSE) down

logs: ## Follow logs of all services
	$(COMPOSE) logs -f

ps: ## Show service status
	$(COMPOSE) ps

lint: ## Lint backend and frontend
	cd backend && uv run ruff check .
	cd frontend && npm run lint

format: ## Auto-format backend and frontend
	cd backend && uv run ruff format . && uv run ruff check --fix .
	cd frontend && npm run format

typecheck: ## Type-check backend (mypy strict) and frontend (tsc strict)
	cd backend && uv run mypy
	cd frontend && npm run typecheck

test: ## Run backend and frontend tests
	cd backend && uv run pytest
	cd frontend && npm test

audit: ## Security checks: bandit, pip-audit, npm audit
	cd backend && uv run bandit -q -c pyproject.toml -r .
	cd backend && uv export --frozen --no-dev -q | uv run pip-audit --disable-pip -r /dev/stdin
	cd frontend && npm audit --audit-level=high

check: lint typecheck test audit ## Everything CI runs (except secret scan and image builds)
	cd backend && uv run ruff format --check .
	cd frontend && npm run format:check
