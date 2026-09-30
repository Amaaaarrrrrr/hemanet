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

**Phase E0: Repository & tooling.** The stack starts, but the API and worker are placeholders
with no application functionality. See [docs/development-status.md](docs/development-status.md).

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
cp .env.example .env        # local placeholders only; .env is git-ignored
docker compose up -d --build   # or: podman-compose up -d --build   (or: make up)
```

| Service | URL | Notes |
|---|---|---|
| API | http://127.0.0.1:8000/ | E0 placeholder JSON |
| Frontend | http://127.0.0.1:5173/ | Vite dev server, E0 placeholder page |
| Mailpit | http://127.0.0.1:8025/ | Captures all development email (SMTP on 1025) |
| PostgreSQL | 127.0.0.1:5432 | Credentials from `.env` |
| Worker | — | `docker compose logs worker` shows heartbeats |

Stop with `docker compose down` (add `-v` to delete the database volume).

## Testing and checks

```bash
make check      # lint, type-check, tests, security audits, format checks
make help       # list all targets
```

Or run them per project: see [backend/README.md](backend/README.md) and the `scripts` section of
`frontend/package.json`. CI runs the same checks plus a gitleaks secret scan and a container-stack
smoke test.

## Contributing

HemaNet is built in approved phases. Read [CONTRIBUTING.md](CONTRIBUTING.md) before making changes.

## Known limitations (E0)

- The API, worker and frontend are placeholders; no domain functionality exists yet.
- The frontend container bakes the source into the image; there's no hot reload from host
  files yet.
- There's no production frontend image yet (deployment work is phase E21).
- The reference `HemaNet MVP.pdf` cited by the blueprint hasn't been added to the repository yet.
