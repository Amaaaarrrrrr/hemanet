# ADR-013 — No patient identifiers in the MVP

- **Status:** Accepted
- **Date:** 2026-09-30
- **Source:** [Blueprint §AB](../blueprint/12-architecture-decisions.md) (text carried over verbatim)

- **Decision:** Requests carry the component, recipient ABO/Rh, quantity, urgency and an optional hospital reference, never patient name/ID/diagnosis. No prescription uploads.
- **Reason:** Data minimisation; coordination doesn't need patient identity; it greatly reduces regulatory burden and breach impact.
- **Consequences:** Patient-level traceability stays in hospital systems; future integration requires a legal basis.
