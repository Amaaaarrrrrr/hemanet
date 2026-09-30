# ADR-015 — Portable container deployment; hosting decided after legal review

- **Status:** Accepted
- **Date:** 2026-09-30
- **Source:** [Blueprint §AB](../blueprint/12-architecture-decisions.md) (text carried over verbatim)

- **Decision:** Docker images; only standard Postgres and S3-compatible storage; no proprietary managed services in core logic. AWS (PDF) or an in-Kenya provider is chosen after AS-40 is answered.
- **Reason:** Data-residency uncertainty; avoiding lock-in.
