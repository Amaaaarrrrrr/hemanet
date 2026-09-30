# ADR-003 — PostgreSQL as system of record, job queue and outbox

- **Status:** Accepted
- **Date:** 2026-09-30
- **Source:** [Blueprint §AB](../blueprint/12-architecture-decisions.md) (text carried over verbatim)

- **Decision:** Use Postgres tables (`jobs`, `outbox_events`) with `FOR UPDATE SKIP LOCKED` for background work and events. No Redis/Celery/SQS in the MVP.
- **Alternatives:** Celery + Redis (more moving parts, and no transactional guarantee between the DB write and enqueue); AWS SQS (vendor lock-in conflicts with the residency uncertainty).
- **Reason:** Events are enqueued atomically with state changes (transactional outbox), one fewer service to operate and secure, and ample throughput at pilot scale (thousands of jobs/minute).
- **Consequences:** Must monitor queue depth; if throughput needs grow, swap the job backend behind the `jobs` interface.
