# ADR-014 — flask-smorest + marshmallow; OpenAPI-generated TypeScript types

- **Status:** Accepted
- **Date:** 2026-09-30
- **Source:** [Blueprint §AB](../blueprint/12-architecture-decisions.md) (text carried over verbatim)

- **Decision:** API schemas defined once in marshmallow; the OpenAPI spec is generated; the frontend uses `openapi-typescript`.
- **Alternatives:** Pydantic + flask-openapi3/spectree (good typing, less mature Flask integration); hand-written TS types (drift).
- **Reason:** Mature Flask integration, a single source of truth, and CI can detect breaking API changes, which protects future mobile clients.
