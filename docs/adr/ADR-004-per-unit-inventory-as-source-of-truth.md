# ADR-004 — Per-unit inventory as source of truth

- **Status:** Accepted
- **Date:** 2026-09-30
- **Source:** [Blueprint §AB](../blueprint/12-architecture-decisions.md) (text carried over verbatim)

- **Decision:** `blood_units` rows are the truth; totals are derived (view). Batches are labels on units.
- **Alternatives:** Aggregate counts (PDF), which can't track expiry per unit; separate batch-quantity stock (two sources of truth).
- **Reason:** Correct expiry handling, traceability, prevention of double allocation, a foundation for QR, recall and transfers. Confirmed by your decision 5.
- **Consequences:** More data entry (R-03), so we invest in scanner/CSV entry. Counts are queries (indexed, cheap at pilot scale).
