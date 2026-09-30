# ADR-016 — UUID primary keys + human reference codes

- **Status:** Accepted
- **Date:** 2026-09-30
- **Source:** [Blueprint §AB](../blueprint/12-architecture-decisions.md) (text carried over verbatim)

- **Decision:** UUIDs for entity IDs; `reference_code` (e.g., `REQ-2026-000123`) for humans and phone calls; bigint identities for append-only logs.
- **Reason:** Non-enumerable IDs (defence in depth against IDOR), merge-friendly, readable references for operations.
