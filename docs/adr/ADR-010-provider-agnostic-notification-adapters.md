# ADR-010 — Provider-agnostic notification adapters

- **Status:** Accepted
- **Date:** 2026-09-30
- **Source:** [Blueprint §AB](../blueprint/12-architecture-decisions.md) (text carried over verbatim)

- **Decision:** `EmailProvider`/`SmsProvider` interfaces; dev mocks; providers selected by config; secondary SMS provider supported.
- **Reason:** Kenyan SMS market specifics (e.g., Africa's Talking vs Twilio: cost, sender IDs, delivery), failover, testability.
