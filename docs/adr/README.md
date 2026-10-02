# Architecture Decision Records

Each significant architectural decision is recorded as an individual ADR.
ADR-001 to ADR-018 were proposed in [blueprint §AB](../blueprint/12-architecture-decisions.md)
and **accepted by the project owner on 2026-09-30**, together with the 11 decisions listed in
[13-delivery-plan.md § "Decisions needed from you"](../blueprint/13-delivery-plan.md).

New decisions are added as new files using [ADR-000-template.md](ADR-000-template.md).
Accepted ADRs are not rewritten; a change of direction is a new ADR that supersedes the old one.

Records are in two groups:

- **Architecture decisions:** ADR-001 to ADR-018, from blueprint §AB, approved by the project
  owner.
- **Technical/tooling decisions:** ADR-019 onward, made during implementation phases. These choose
  tools and versions *within* the approved architecture and never override ADR-001 to ADR-018.

## Architecture decisions (blueprint §AB, accepted 2026-09-30)

| ADR | Title | Status |
|---|---|---|
| [ADR-001](ADR-001-modular-monolith.md) | Modular monolith | Accepted |
| [ADR-002](ADR-002-domain-first-module-layout.md) | Domain-first module layout | Accepted |
| [ADR-003](ADR-003-postgresql-as-system-of-record-job-queue-and-outbox.md) | PostgreSQL as system of record, job queue and outbox | Accepted |
| [ADR-004](ADR-004-per-unit-inventory-as-source-of-truth.md) | Per-unit inventory as source of truth | Accepted |
| [ADR-005](ADR-005-clinical-rules-as-versioned-validated-configuration.md) | Clinical rules as versioned, validated configuration | Accepted |
| [ADR-006](ADR-006-separate-fulfilment-and-mobilisation.md) | Separate fulfilment and mobilisation | Accepted |
| [ADR-007](ADR-007-short-lived-jwt-access-rotating-opaque-refresh-tokens.md) | Short-lived JWT access + rotating opaque refresh tokens | Accepted |
| [ADR-008](ADR-008-facility-scoped-rbac-with-permission-codes.md) | Facility-scoped RBAC with permission codes | Accepted |
| [ADR-009](ADR-009-coordinates-haversine-now-postgis-in-v1.md) | Coordinates + haversine now, PostGIS in V1 | Accepted |
| [ADR-010](ADR-010-provider-agnostic-notification-adapters.md) | Provider-agnostic notification adapters | Accepted |
| [ADR-011](ADR-011-append-only-hash-chained-audit-no-blockchain.md) | Append-only hash-chained audit; no blockchain | Accepted |
| [ADR-012](ADR-012-polling-instead-of-websockets-in-the-mvp.md) | Polling instead of WebSockets in the MVP | Accepted |
| [ADR-013](ADR-013-no-patient-identifiers-in-the-mvp.md) | No patient identifiers in the MVP | Accepted |
| [ADR-014](ADR-014-flask-smorest-marshmallow-openapi-generated-typescript-types.md) | flask-smorest + marshmallow; OpenAPI-generated TypeScript types | Accepted |
| [ADR-015](ADR-015-portable-container-deployment.md) | Portable container deployment; hosting decided after legal review | Accepted |
| [ADR-016](ADR-016-uuid-primary-keys-human-reference-codes.md) | UUID primary keys + human reference codes | Accepted |
| [ADR-017](ADR-017-eligibility-is-a-three-state-indication-never-a-clearance.md) | Eligibility is a three-state *indication*, never a clearance | Accepted |
| [ADR-018](ADR-018-staff-in-the-loop-for-high-impact-actions.md) | Staff-in-the-loop for high-impact actions | Accepted |

## Technical/tooling decisions (made during implementation)

| ADR | Title | Phase | Status |
|---|---|---|---|
| [ADR-019](ADR-019-tooling-baseline.md) | Tooling baseline | E0 | Accepted |
| [ADR-020](ADR-020-application-generated-uuidv7.md) | Application-generated UUIDv7 | E1a | Accepted |
