# ADR-006 — Separate fulfilment and mobilisation

- **Status:** Accepted
- **Date:** 2026-09-30
- **Source:** [Blueprint §AB](../blueprint/12-architecture-decisions.md) (text carried over verbatim)

- **Decision:** Requests are fulfilled only from released inventory. Donor appeals replenish inventory and are linked to, but not equal to, requests.
- **Reason:** Donated blood must be collected and processed before use; a donor's "accept" isn't supply. Confirmed by your decision 4.
- **Consequences:** Two state machines; the link is `appeals.related_request_id`. Direct patient-directed donation isn't modelled (AS-18).
