# ADR-011 — Append-only hash-chained audit; no blockchain

- **Status:** Accepted
- **Date:** 2026-09-30
- **Source:** [Blueprint §AB](../blueprint/12-architecture-decisions.md) (text carried over verbatim)

- **Decision:** DB-level append-only audit and unit events with hash chaining and optional external anchoring.
- **Alternatives:** Blockchain (PDF future enhancement): no trust boundary between mutually distrusting writers that needs it, plus high operational complexity and privacy risk from immutable personal data on a ledger.
- **Reason:** Tamper-evidence at a fraction of the cost; personal data stays deletable/pseudonymisable where the law requires.
