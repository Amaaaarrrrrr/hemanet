# Backend foundation (Phase E1a)

What the backend provides before any domain feature exists, and the conventions
every later module must follow. Blueprint references: §P (module map), §N.1 (API
conventions), §E (data conventions), §R.2 (security controls), §S.1 (testing),
ADR-001/002/003/014/016/020.

## Layout

```
backend/
├── app/
│   ├── __init__.py        create_app() factory
│   ├── config.py          typed settings (pydantic-settings)
│   ├── extensions.py      db (Flask-SQLAlchemy), migrate, api (flask-smorest), cors
│   ├── models.py          imports every model for Alembic
│   ├── health.py          /healthz, /readyz
│   ├── core/              shared kernel, no domain logic
│   │   ├── api.py           Blueprint with a strict argument parser
│   │   ├── clock.py         injectable clock (UTC)
│   │   ├── concurrency.py   If-Match / ETag helpers
│   │   ├── db.py            Base, naming conventions, mixins, DbSession
│   │   ├── errors.py        error envelope + exception mapping
│   │   ├── idempotency.py   Idempotency-Key decorator + table
│   │   ├── ids.py           UUIDv7 generator (ADR-020)
│   │   ├── logging.py       structlog JSON + redaction
│   │   ├── outbox.py        transactional outbox table + publish_event()
│   │   ├── pagination.py    cursor pagination
│   │   ├── request_context.py  X-Request-ID + request log line
│   │   └── security_headers.py
│   ├── jobs/              job queue, outbox dispatch, scheduler, worker loop, CLI
│   └── modules/           domain modules (empty until the first domain phase)
├── migrations/            Alembic (via Flask-Migrate)
├── tests/                 unit/ api/ integration/ concurrency/ migrations/ support/
├── wsgi.py                api entry point (gunicorn)
└── worker.py              worker entry point
```

Import boundaries are enforced in CI by import-linter: `app.core` may not import
`app.jobs`, `app.modules`, `app.health` or `app.extensions`, and `app.jobs` may not
import `app.modules`. Contracts between domain modules (§P.2) are added as the
modules are created.

## Configuration

Settings come from environment variables (see `.env.example`). `APP_ENV` is one of
`local | ci | staging | pilot | production`. Outside `local`/`ci` the app refuses to
start with wildcard or non-HTTPS CORS origins, placeholder credentials
(`change-me`…) or non-JSON logs. Configuration errors never echo values (the
database URL contains a password). The OpenAPI document is published at
`/api/v1/openapi.json` except in `pilot`/`production`.

## Data conventions

* `Base` uses deterministic constraint names (`pk_`, `fk_`, `uq_`, `ck_`, `ix_`) so
  migrations are stable.
* `UUIDPrimaryKeyMixin`: UUIDv7 ids generated in the application (ADR-020). Id order
  is for index locality only; **never sort by id as a business rule**. Lists sort by
  explicit timestamps with the id as a tie-breaker.
* `TimestampMixin`: `created_at`/`updated_at` (`timestamptz`) from the injectable
  clock, with `now()` database defaults as a backstop.
* `VersionMixin`: optimistic locking via SQLAlchemy `version_id_col`.
* Infrastructure tables use `bigint` identity keys (§E).

### Tables created in E1a

| Table | Purpose |
|---|---|
| `jobs` | Job queue (`job_status` enum: QUEUED, RUNNING, SUCCEEDED, FAILED, DEAD) |
| `outbox_events` | Transactional outbox |
| `worker_heartbeats` | One row per live worker; read by `/readyz` (addition to §E.10) |
| `idempotency_keys` | Stored responses for idempotent POSTs |

**Staged migration:** `idempotency_keys.user_id` has **no foreign key yet**, because
the `users` table arrives in E2. The E2 migration adds
`fk_idempotency_keys_user_id_users`. This is intentional, not an omission.

## API conventions implemented

* **Error envelope** `{"error": {code, message, details, request_id}}` for every
  error. Messages are generic; stack traces are logged, never returned.
  Codes follow §N.1, plus three additions for plain HTTP errors:
  `METHOD_NOT_ALLOWED` (405), `PAYLOAD_TOO_LARGE` (413), `UNSUPPORTED_MEDIA_TYPE` (415).
  * Schema validation returns **400** `VALIDATION_ERROR`/`UNKNOWN_FIELD`. flask-smorest
    would return 422, but §N.1 reserves 422 for `BUSINESS_RULE_VIOLATION`.
  * Database outages return 503 `SERVICE_UNAVAILABLE`; ORM version conflicts 409
    `VERSION_CONFLICT`.
* **Unknown fields are rejected everywhere** (JSON body *and* query string). Route
  modules must use `app.core.api.Blueprint`, whose parser enforces this;
  webargs' default silently drops unknown query parameters.
* **Request IDs**: every response has `X-Request-ID` (a safe client-supplied value is
  echoed; otherwise a new UUIDv7). Logs carry the same id.
* **Pagination**: `?limit=` (default 25, max 100) and an opaque `?cursor=`; responses
  are `{"data": [...], "page": {"next_cursor", "limit"}}`. Keyset-based, so pages stay
  correct while rows are added.
* **Optimistic concurrency**: `require_if_match(version)` returns 400 if `If-Match` is
  missing or invalid and 409 `VERSION_CONFLICT` if stale; responses carry
  `ETag: "<version>"`.
* **Idempotency**: `@idempotent(principal=…)` requires `Idempotency-Key`, replays the
  stored 2xx response for 24 h (`Idempotent-Replayed: true`), returns 409
  `IDEMPOTENCY_KEY_REUSED` if the key is reused for a different request, and releases
  the key when the request fails. Concurrent duplicates wait on the key's unique index
  and then replay. The decorator owns the transaction.
  *Open point for E15:* keys are scoped per user, but the public appeal-response link
  (`/r/:token`) has no user; E15 must decide its idempotency scope.
* **Request bodies** are limited to 1 MB (`MAX_CONTENT_LENGTH_BYTES`).

## Security headers and CORS

Every response has a deny-all CSP (`default-src 'none'; frame-ancestors 'none'`),
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy: strict-origin-when-cross-origin`, a restrictive `Permissions-Policy`,
`Cross-Origin-Opener-Policy: same-origin` and `Cache-Control: no-store`. HSTS is added
outside `local`/`ci`. CORS applies to `/api/*` only, with an explicit origin allow-list
and no wildcard.

## Logging

structlog JSON on stdout for both app and library logs. A redaction step runs last:
values of sensitive keys (names, phone numbers, emails, notes, tokens, passwords…) become
`[REDACTED]`, and emails, phone numbers, bearer tokens, JWTs and database-URL
passwords are scrubbed from any remaining text, including exception messages. The
request log records method, path (never the query string), status and duration.
SQL statement logging is disabled.

## Background work (ADR-003)

* `enqueue()` writes a job in the caller's transaction (atomic with the caller's work).
  An optional `dedupe_key` makes enqueueing idempotent.
* Workers claim jobs with `SELECT … FOR UPDATE SKIP LOCKED` and commit the claim
  immediately. Two workers never get the same job; this is tested with genuinely
  concurrent database sessions.
* A handler runs in one transaction; success is recorded in that same transaction.
  On error, the handler's writes roll back and the job becomes FAILED with an
  exponential backoff (30 s, doubling, capped at 1 h), then DEAD after
  `max_attempts` (default 5). `PermanentJobError` goes straight to DEAD. Stored
  errors are redacted and truncated.
* A job whose lock expired (worker crashed) can be reclaimed; the old worker can no
  longer complete it.
* **Outbox:** `publish_event()` adds an event to the caller's transaction. The worker
  turns each committed event into one `outbox.handle` job per registered handler
  (deduplicated), so handlers reuse the queue's retries. Delivery is at-least-once,
  so handlers must be idempotent. No handlers exist yet.
* **Scheduler:** every worker enqueues due recurring jobs; per-slot dedupe keys mean
  each slot runs once however many workers run. Currently there is one schedule: an
  hourly purge of expired idempotency keys.
* **Heartbeat:** each worker upserts `worker_heartbeats` every
  `WORKER_HEARTBEAT_SECONDS` and deletes its row on graceful shutdown.
* **Shutdown:** SIGTERM/SIGINT wake the idle wait immediately; a running job finishes
  first. Database errors are logged and retried without losing work.
* Operator commands: `flask jobs enqueue-noop`, `flask jobs status`.

## Health

| Endpoint | Checks | Response |
|---|---|---|
| `GET /healthz` | Process is up (no database access) | 200 `{"status":"ok"}` |
| `GET /readyz` | Database reachable, migrations at head, a worker heartbeat newer than `READINESS_HEARTBEAT_MAX_AGE_SECONDS` | 200 `{"status":"ready"}` or 503 `{"status":"not_ready"}` |

Neither endpoint reveals which check failed; that is logged server-side. Both are
served at the root, not under `/api/v1`, because they are operational endpoints.

## Migrations

Alembic through Flask-Migrate (`flask db …`). Batch mode is off (PostgreSQL only).
Locally, the one-shot `migrate` compose service runs `flask db upgrade` before
`api`/`worker` start, matching the "release task" approach in §T.3. Docker Compose
enforces that ordering; podman-compose may start them concurrently, which is safe
because `/readyz` stays not-ready and the worker retries until the schema exists.
Migration files are named `YYYYMMDD_<rev>_<slug>.py`. Every migration must
downgrade cleanly (including enum types).

## Tests

```bash
make up      # the tests need the compose postgres
make test    # derives TEST_DATABASE_URL (…/hemanet_test) from .env
```

* Real PostgreSQL, never SQLite. The `*_test` database is dropped and recreated each
  run; the suite refuses any other database name.
* Each test runs in a transaction that is rolled back (commits inside become
  savepoints). Tests marked `concurrency` use real commits across threads or
  processes and truncate afterwards.
* Migration tests: upgrade from empty, downgrade to base and upgrade again, model/
  migration drift (`compare_metadata`), single head.
* Test-only routes (`tests/support/routes.py`) exercise the error envelope,
  idempotency, If-Match and pagination end to end; they are never registered in the
  real app.

## Deferred decisions

| Decision | Deferred to | Notes |
|---|---|---|
| Rate limiting implementation | **E2** | §R.2 names "Flask-Limiter with Postgres-backed counters", but Flask-Limiter has no Postgres storage. Decide in E2, when login/OTP endpoints exist. No Redis or other external rate-limit service. |
| `idempotency_keys.user_id` foreign key | **E2** | Added by the migration that creates `users`. |
| Idempotency scope for public token endpoints | **E15** | The appeal-response link has no user. |
