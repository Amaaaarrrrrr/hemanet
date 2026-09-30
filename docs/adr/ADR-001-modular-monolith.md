# ADR-001 — Modular monolith

- **Status:** Accepted
- **Date:** 2026-09-30
- **Source:** [Blueprint §AB](../blueprint/12-architecture-decisions.md) (text carried over verbatim)

- **Decision:** A single Flask codebase with strict domain modules, deployed as `api` + `worker` processes.
- **Context:** One team, early product, domain boundaries still being learned.
- **Alternatives:** Microservices (premature: operational cost and distributed transactions around inventory); a single flat Flask app (becomes unmaintainable).
- **Reason:** Fast iteration, one transaction boundary for inventory integrity, and module boundaries enforced by import-linter so services can be extracted later.
- **Consequences:** Scaling is vertical plus horizontal replicas; extraction candidates later: notifications, matching, integrations.
