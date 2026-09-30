# ADR-008 — Facility-scoped RBAC with permission codes

- **Status:** Accepted
- **Date:** 2026-09-30
- **Source:** [Blueprint §AB](../blueprint/12-architecture-decisions.md) (text carried over verbatim)

- **Decision:** Roles map to permissions (data); memberships bind user + role + facility; policy checks combine permission, scope, state and capability.
- **Reason:** "Role ≠ permission" (master §25); users can belong to multiple facilities; validated role responsibilities (AS-17) can be applied without code changes.
- **Consequences:** Needs an exhaustive authz test matrix (planned).
