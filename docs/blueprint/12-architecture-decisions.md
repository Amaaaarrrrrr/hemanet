# 12 — AB. Architectural Decisions and Trade-offs (ADR log)

Status for all: **Accepted** (2026-09-30). Each is now an individual record in
[`docs/adr/`](../adr/README.md), which is the authoritative copy; later decisions are added there only.

---

### ADR-001 — Modular monolith
- **Decision:** A single Flask codebase with strict domain modules, deployed as `api` + `worker` processes.
- **Context:** One team, early product, domain boundaries still being learned.
- **Alternatives:** Microservices (premature: operational cost and distributed transactions around inventory); a single flat Flask app (becomes unmaintainable).
- **Reason:** Fast iteration, one transaction boundary for inventory integrity, and module boundaries enforced by import-linter so services can be extracted later.
- **Consequences:** Scaling is vertical plus horizontal replicas; extraction candidates later: notifications, matching, integrations.

### ADR-002 — Domain-first module layout
- **Decision:** `app/modules/<domain>/{models,schemas,repository,domain,service,policies,routes}` instead of layer-first top-level folders.
- **Alternatives:** The suggested hybrid layout (layers + domains side by side).
- **Reason:** Each feature lives in one place; ownership of models is clear; cross-module access only through services and events.
- **Consequences:** Some shared utilities live in `core/`; discipline is needed so `core` doesn't grow domain logic.

### ADR-003 — PostgreSQL as system of record, job queue and outbox
- **Decision:** Use Postgres tables (`jobs`, `outbox_events`) with `FOR UPDATE SKIP LOCKED` for background work and events. No Redis/Celery/SQS in the MVP.
- **Alternatives:** Celery + Redis (more moving parts, and no transactional guarantee between the DB write and enqueue); AWS SQS (vendor lock-in conflicts with the residency uncertainty).
- **Reason:** Events are enqueued atomically with state changes (transactional outbox), one fewer service to operate and secure, and ample throughput at pilot scale (thousands of jobs/minute).
- **Consequences:** Must monitor queue depth; if throughput needs grow, swap the job backend behind the `jobs` interface.

### ADR-004 — Per-unit inventory as source of truth
- **Decision:** `blood_units` rows are the truth; totals are derived (view). Batches are labels on units.
- **Alternatives:** Aggregate counts (PDF), which can't track expiry per unit; separate batch-quantity stock (two sources of truth).
- **Reason:** Correct expiry handling, traceability, prevention of double allocation, a foundation for QR, recall and transfers. Confirmed by your decision 5.
- **Consequences:** More data entry (R-03), so we invest in scanner/CSV entry. Counts are queries (indexed, cheap at pilot scale).

### ADR-005 — Clinical rules as versioned, validated configuration
- **Decision:** Compatibility, eligibility, component specs and urgency live in `rule_sets` with the lifecycle DRAFT → PENDING_VALIDATION → VALIDATED → ACTIVE → RETIRED. Code implements rule *types*; data supplies *values*. Separation of duties and an environment guard apply.
- **Alternatives:** Hardcoded tables (violates the master instruction; unsafe); a free-form rules engine/DSL (over-engineered, and hard to validate for non-engineers).
- **Reason:** Validated rules can change without code deploys; every decision is reproducible (pinned rule-set IDs); there's a clear accountability trail.
- **Consequences:** New *types* of rule still need code; the admin UI must present tables clearly for clinical reviewers.

### ADR-006 — Separate fulfilment and mobilisation
- **Decision:** Requests are fulfilled only from released inventory. Donor appeals replenish inventory and are linked to, but not equal to, requests.
- **Reason:** Donated blood must be collected and processed before use; a donor's "accept" isn't supply. Confirmed by your decision 4.
- **Consequences:** Two state machines; the link is `appeals.related_request_id`. Direct patient-directed donation isn't modelled (AS-18).

### ADR-007 — Short-lived JWT access + rotating opaque refresh tokens
- **Decision:** 15-min JWT in memory; DB-stored, hashed, rotating refresh tokens (cookie for web, body for mobile); permissions resolved server-side per request.
- **Alternatives:** Server-side sessions only (simple for web, awkward for mobile); long-lived JWTs (no revocation).
- **Reason:** One mechanism for web and mobile, immediate revocation via `token_version` + refresh revocation, and no permissions baked into tokens.
- **Consequences:** Refresh logic in the frontend client; CSRF protection on refresh endpoints.

### ADR-008 — Facility-scoped RBAC with permission codes
- **Decision:** Roles map to permissions (data); memberships bind user + role + facility; policy checks combine permission, scope, state and capability.
- **Reason:** "Role ≠ permission" (master §25); users can belong to multiple facilities; validated role responsibilities (AS-17) can be applied without code changes.
- **Consequences:** Needs an exhaustive authz test matrix (planned).

### ADR-009 — Coordinates + haversine now, PostGIS in V1
- **Decision:** Store `latitude/longitude` numerics; compute distance with bounding box + haversine SQL behind `geo.find_within_radius()`. Introduce PostGIS (geography column + GiST index, backfilled by migration) when radius queries or transfer planning need it.
- **Alternatives:** PostGIS from day one (small cost, but adds an extension dependency to every environment and more to learn); external maps APIs for distance (cost, latency, dependency, privacy).
- **Reason:** Adequate at pilot scale; the migration path is trivial because the interface is stable.
- **Consequences:** Straight-line distance only (not travel time); acceptable for ranking.

### ADR-010 — Provider-agnostic notification adapters
- **Decision:** `EmailProvider`/`SmsProvider` interfaces; dev mocks; providers selected by config; secondary SMS provider supported.
- **Reason:** Kenyan SMS market specifics (e.g., Africa's Talking vs Twilio: cost, sender IDs, delivery), failover, testability.

### ADR-011 — Append-only hash-chained audit; no blockchain
- **Decision:** DB-level append-only audit and unit events with hash chaining and optional external anchoring.
- **Alternatives:** Blockchain (PDF future enhancement): no trust boundary between mutually distrusting writers that needs it, plus high operational complexity and privacy risk from immutable personal data on a ledger.
- **Reason:** Tamper-evidence at a fraction of the cost; personal data stays deletable/pseudonymisable where the law requires.

### ADR-012 — Polling instead of WebSockets in the MVP
- **Decision:** TanStack Query polling at 15–60 s; SSE in V1 fed by outbox events.
- **Reason:** Simpler infrastructure (no sticky sessions or connection management); the latency needs of the MVP workflows are measured in minutes, not milliseconds.
- **Consequences:** Slightly higher request volume, mitigated by cheap endpoints and pausing when the tab is hidden.

### ADR-013 — No patient identifiers in the MVP
- **Decision:** Requests carry the component, recipient ABO/Rh, quantity, urgency and an optional hospital reference, never patient name/ID/diagnosis. No prescription uploads.
- **Reason:** Data minimisation; coordination doesn't need patient identity; it greatly reduces regulatory burden and breach impact.
- **Consequences:** Patient-level traceability stays in hospital systems; future integration requires a legal basis.

### ADR-014 — flask-smorest + marshmallow; OpenAPI-generated TypeScript types
- **Decision:** API schemas defined once in marshmallow; the OpenAPI spec is generated; the frontend uses `openapi-typescript`.
- **Alternatives:** Pydantic + flask-openapi3/spectree (good typing, less mature Flask integration); hand-written TS types (drift).
- **Reason:** Mature Flask integration, a single source of truth, and CI can detect breaking API changes, which protects future mobile clients.

### ADR-015 — Portable container deployment; hosting decided after legal review
- **Decision:** Docker images; only standard Postgres and S3-compatible storage; no proprietary managed services in core logic. AWS (PDF) or an in-Kenya provider is chosen after AS-40 is answered.
- **Reason:** Data-residency uncertainty; avoiding lock-in.

### ADR-016 — UUID primary keys + human reference codes
- **Decision:** UUIDs for entity IDs; `reference_code` (e.g., `REQ-2026-000123`) for humans and phone calls; bigint identities for append-only logs.
- **Reason:** Non-enumerable IDs (defence in depth against IDOR), merge-friendly, readable references for operations.

### ADR-017 — Eligibility is a three-state *indication*, never a clearance
- **Decision:** Output is always `POTENTIALLY_ELIGIBLE / POTENTIALLY_INELIGIBLE / REQUIRES_REVIEW`; missing data → REQUIRES_REVIEW; screening at the collection site is authoritative.
- **Reason:** Master §16/§49; HemaNet must not make medical decisions.

### ADR-018 — Staff-in-the-loop for high-impact actions
- **Decision:** The system *suggests* allocations and appeals; humans reserve, issue and launch. No automatic re-routing, auto-waves or transfers.
- **Reason:** Safety, cost control, validation pending; automation can be enabled per facility later once it's trusted.
