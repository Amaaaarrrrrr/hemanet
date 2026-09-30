# ADR-012 — Polling instead of WebSockets in the MVP

- **Status:** Accepted
- **Date:** 2026-09-30
- **Source:** [Blueprint §AB](../blueprint/12-architecture-decisions.md) (text carried over verbatim)

- **Decision:** TanStack Query polling at 15–60 s; SSE in V1 fed by outbox events.
- **Reason:** Simpler infrastructure (no sticky sessions or connection management); the latency needs of the MVP workflows are measured in minutes, not milliseconds.
- **Consequences:** Slightly higher request volume, mitigated by cheap endpoints and pausing when the tab is hidden.
