# Development status

Phases follow [blueprint §AE](blueprint/13-delivery-plan.md). Each phase is committed only after
the project owner's explicit approval.

| Step | Phase | Status |
|---|---|---|
| 1 | **E0**: repository, compose stack, CI skeleton, ADRs | **Done** (`c029336`, 2026-09-30) |
| 2 | **E1a** (E1.1–1.7): backend foundation | **Awaiting approval** |
| 3 | **E1b** (E1.8–1.9): frontend shell & design system | Not started (begins after E1a is committed) |
| 4 | E4.1: audit | Not started |
| 5 | E2.1–2.5, 2.8: authentication | Not started |
| 6–24 | See blueprint §AE | Not started |

E1 is split into two phases (E1a backend, E1b frontend), each with its own review,
approval and commit (owner decision, 2026-10-02).

## E1a: Backend foundation

**Gate:** `/healthz` and `/readyz` work; error-envelope tests pass; the worker processes a
no-op job; two workers can't claim the same job.

Delivered: app factory and typed settings; SQLAlchemy/Alembic with naming conventions and
mixins; UUIDv7 ids (ADR-020); error envelope; request IDs; redacting JSON logs; security
headers and CORS; cursor pagination; If-Match; idempotency keys; Postgres job queue with
`SKIP LOCKED`, retries, outbox dispatch, scheduler, heartbeats and graceful shutdown;
health probes; real-Postgres tests including concurrency and migration checks;
import-linter. Details: [backend-foundation.md](backend-foundation.md).

## Deferred decisions

| Decision | Deferred to | Recorded in |
|---|---|---|
| Rate-limiting implementation (no Redis or external service) | E2 | [backend-foundation.md](backend-foundation.md#deferred-decisions) |
| Foreign key `idempotency_keys.user_id` → `users` (staged migration) | E2 | same |
| Idempotency scope for public token endpoints (`/r/:token`) | E15 | same |

## E0: Repository & tooling (done)

Monorepo layout, compose stack, CI skeleton, ADR-001 to ADR-018 accepted and recorded,
ADR-019 tooling baseline.
