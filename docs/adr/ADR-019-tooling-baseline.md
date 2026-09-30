# ADR-019 — Tooling baseline

- **Type:** Technical/tooling decision. It isn't one of the blueprint architecture decisions
  (ADR-001 to ADR-018). It selects tools and versions within that architecture and doesn't change it.
- **Status:** Accepted
- **Date:** 2026-09-30
- **Phase:** E0 (repository & tooling)

- **Decision:**
  - Python **3.13** in containers and CI; backend dependencies managed and locked with **uv** (`backend/uv.lock`).
  - Node **22 LTS**; frontend dependencies managed and locked with **npm** (`frontend/package-lock.json`).
  - PostgreSQL **16** for every environment, including local and CI (never SQLite).
  - GNU **make** is the documented entry point for local developer commands (`Makefile`).
  - One root `compose.yaml` that works with both **Docker Compose v2** and **podman-compose**; all host ports bound to `127.0.0.1`.
  - One backend image serves both the `api` and `worker` processes (ADR-001).
  - CI on **GitHub Actions**: ruff, ruff format, mypy (strict), pytest, bandit, pip-audit; eslint, prettier, tsc (strict), vitest, vite build, npm audit; gitleaks; container-stack smoke test.
- **Context:** Blueprint §AD items 0.1–0.3 and §P.3 name the quality gates but not the package managers or runtime versions. The primary development machine runs Fedora with Podman rather than Docker.
- **Alternatives:** pip-tools or Poetry (slower, or with heavier project metadata); pnpm (would add another global tool); Python 3.14 (newest, but wheel coverage for the future dependency set is less certain).
- **Reason:** uv gives fast, reproducible, hash-locked installs with one tool. npm ships with Node. Python 3.13 is mature and fully supported by the planned dependencies. Supporting both Podman and Docker keeps the stack portable (ADR-015).
- **Consequences:** Contributors need `make`, `uv` and Node 22 on the host to run checks outside containers. Container images pin the uv minor version (`ghcr.io/astral-sh/uv:0.12`). Upgrading Python or Node is a deliberate change recorded in a new ADR.
