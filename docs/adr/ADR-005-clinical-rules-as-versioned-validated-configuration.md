# ADR-005 — Clinical rules as versioned, validated configuration

- **Status:** Accepted
- **Date:** 2026-09-30
- **Source:** [Blueprint §AB](../blueprint/12-architecture-decisions.md) (text carried over verbatim)

- **Decision:** Compatibility, eligibility, component specs and urgency live in `rule_sets` with the lifecycle DRAFT → PENDING_VALIDATION → VALIDATED → ACTIVE → RETIRED. Code implements rule *types*; data supplies *values*. Separation of duties and an environment guard apply.
- **Alternatives:** Hardcoded tables (violates the master instruction; unsafe); a free-form rules engine/DSL (over-engineered, and hard to validate for non-engineers).
- **Reason:** Validated rules can change without code deploys; every decision is reproducible (pinned rule-set IDs); there's a clear accountability trail.
- **Consequences:** New *types* of rule still need code; the admin UI must present tables clearly for clinical reviewers.
