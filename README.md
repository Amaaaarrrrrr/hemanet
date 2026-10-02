# HemaNet

HemaNet is a blood-resource coordination platform for Kenya. It links hospitals, blood banks and
donors through two related workflows (ADR-006):

- **Fulfilment:** hospital blood request → blood bank → per-unit inventory → allocation →
  reservation → issue → hospital receipt → completion.
- **Mobilisation:** shortage → appeal → explainable donor matching → staff-approved notification →
  donor response → appointment → **staff-recorded** donation → processing → available component.

> **Development-stage prototype.** HemaNet is not clinically validated, medically certified,
> regulatory compliant or hospital-ready. It is a coordination tool, not a clinical
> decision-maker. All clinical rules are configurable placeholders until validated by the
> appropriate Kenyan authorities and stakeholders (ADR-005).

## Current phase

**Phase E1a: Backend foundation** (awaiting approval). The backend infrastructure is in place
(configuration, database and migrations, error handling, logging, background jobs and health
checks), but there is no domain functionality yet: no users, donors, inventory or requests. See
[docs/development-status.md](docs/development-status.md) and
[docs/backend-foundation.md](docs/backend-foundation.md).

## Repository layout

| Path | Contents |
|---|---|
| `backend/` | Python/Flask API and worker (one image, two processes); uv-managed |
| `frontend/` | React + TypeScript + Vite SPA; npm-managed |
| `infra/` | Deployment infrastructure (empty until hosting is decided, ADR-015) |
| `docs/blueprint/` | Product and technical blueprint: the source of truth |
| `docs/adr/` | Architecture Decision Records |
| `compose.yaml` | Local development stack |
| `.github/workflows/` | CI |

## Architecture at a glance

Modular Flask monolith (ADR-001/002) with a separate worker process, PostgreSQL 16 as the system of
record, job queue and outbox (ADR-003), and a React/TypeScript SPA. Local development also runs
Mailpit. There is deliberately no Redis, Celery, microservices, WebSockets or Kubernetes.
Tooling choices are recorded in [ADR-019](docs/adr/ADR-019-tooling-baseline.md).

## Running locally

Prerequisites:

| Tool | Needed for |
|---|---|
| Docker with Compose v2 **or** Podman with `podman-compose` | Running the stack |
| GNU `make` | The documented developer commands (`make up`, `make check`, …) |
| [uv](https://docs.astral.sh/uv/) | Backend dependencies and checks |
| Node 22 LTS with npm | Frontend dependencies and checks |

On Fedora: `sudo dnf install make podman-compose uv`, plus Node 22 from your distribution or a
version manager such as nvm. If you use nvm, make sure `node` and `npm` are on your `PATH` in the
shell where you run `make`.

```bash
make env        # creates .env from .env.example (local placeholders only; git-ignored)
make install    # backend (uv) and frontend (npm) dependencies from the lock files
make up         # builds and starts the stack; migrations run automatically first
```

| Service | URL | Notes |
|---|---|---|
| API | http://127.0.0.1:8000/healthz, `/readyz` | Reloads on backend code changes |
| OpenAPI | http://127.0.0.1:8000/api/v1/openapi.json | Generated from code (ADR-014) |
| Frontend | http://127.0.0.1:5173/ | Vite dev server, placeholder page until E1b |
| Mailpit | http://127.0.0.1:8025/ | Captures all development email (SMTP on 1025) |
| PostgreSQL | 127.0.0.1:5432 | Credentials from `.env` |
| Worker | — | `make logs` shows heartbeats and jobs; `flask jobs enqueue-noop` in the api container queues a test job |
| migrate | — | One-shot: applies migrations, then exits |

Stop with `make down` (`docker compose down -v` / `podman-compose down -v` also deletes the
database volume).

## Testing and checks

```bash
make check      # lint, import boundaries, type-check, tests, security audits, format checks
make help       # list all targets
```

Backend tests run against the compose PostgreSQL (start it with `make up`), in a separate
`hemanet_test` database that is recreated on every run.

Or run them per project: see [backend/README.md](backend/README.md) and the `scripts` section of
`frontend/package.json`. CI runs the same checks plus a gitleaks secret scan and a container-stack
smoke test.

## Contributing

HemaNet is built in approved phases. Read [CONTRIBUTING.md](CONTRIBUTING.md) before making changes.

## Known limitations (E1a)

- There's no domain functionality yet, and the frontend is still a placeholder (E1b).
- There's no rate limiting yet; it's deferred to E2, when the login and OTP endpoints exist.
- The frontend container bakes the source into the image; there's no hot reload from host
  files yet.
- podman-compose doesn't enforce the "migrate finishes first" ordering. The stack still
  converges, because `/readyz` stays not-ready and the worker retries until the schema exists.
- There's no production frontend image yet (deployment work is phase E21).
- The reference `HemaNet MVP.pdf` cited by the blueprint hasn't been added to the repository yet.
