# ADR-017 — Eligibility is a three-state *indication*, never a clearance

- **Status:** Accepted
- **Date:** 2026-09-30
- **Source:** [Blueprint §AB](../blueprint/12-architecture-decisions.md) (text carried over verbatim)

- **Decision:** Output is always `POTENTIALLY_ELIGIBLE / POTENTIALLY_INELIGIBLE / REQUIRES_REVIEW`; missing data → REQUIRES_REVIEW; screening at the collection site is authoritative.
- **Reason:** Master §16/§49; HemaNet must not make medical decisions.
