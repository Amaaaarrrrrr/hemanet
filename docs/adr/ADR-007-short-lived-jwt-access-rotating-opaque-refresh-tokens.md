# ADR-007 — Short-lived JWT access + rotating opaque refresh tokens

- **Status:** Accepted
- **Date:** 2026-09-30
- **Source:** [Blueprint §AB](../blueprint/12-architecture-decisions.md) (text carried over verbatim)

- **Decision:** 15-min JWT in memory; DB-stored, hashed, rotating refresh tokens (cookie for web, body for mobile); permissions resolved server-side per request.
- **Alternatives:** Server-side sessions only (simple for web, awkward for mobile); long-lived JWTs (no revocation).
- **Reason:** One mechanism for web and mobile, immediate revocation via `token_version` + refresh revocation, and no permissions baked into tokens.
- **Consequences:** Refresh logic in the frontend client; CSRF protection on refresh endpoints.
