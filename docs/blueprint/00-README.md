# HemaNet — Technical & Product Blueprint

**Status:** v0.1 — architecture decisions ADR-001 to ADR-018 and the 11 decisions in
[13-delivery-plan.md](13-delivery-plan.md) §"Decisions needed from you" **accepted on 2026-09-30**
(recorded in [docs/adr/](../adr/README.md)). Clinical rules and items marked [VALIDATE] still require
stakeholder validation. Implementation is in progress; see
[docs/development-status.md](../development-status.md) for the current phase.
**Date:** 2026-09-30
**Initial deployment context:** Kenya
**Reference MVP:** `HemaNet MVP.pdf` (4 pages; referred to below as "the PDF")

> HemaNet is a development-stage prototype. It is **not** clinically validated, medically certified,
> regulatory compliant, or hospital-ready. Every clinical rule in this document is a configurable
> placeholder until validated by the appropriate Kenyan authorities and stakeholders.

---

## Label legend

Every feature, rule and design element is tagged with one of these labels:

| Label | Meaning |
|---|---|
| **[CONFIRMED]** | CONFIRMED REQUIREMENT: explicitly stated in the PDF or in your decisions of 2026-09-30 |
| **[PROPOSED]** | PROPOSED IMPROVEMENT: added by this blueprint; needs your approval |
| **[FUTURE]** | FUTURE ENHANCEMENT: designed for (extension point), **not built** in the MVP |
| **[VALIDATE]** | ASSUMPTION REQUIRING VALIDATION: must be confirmed with stakeholders or authorities before real-world use |

A feature can carry two labels, e.g. **[CONFIRMED][VALIDATE]**: required, but the exact rule or workflow still needs validation.

Assumptions are numbered `AS-xx` and listed in full in [11-risks-and-assumptions.md](11-risks-and-assumptions.md).
Architectural decisions are numbered `ADR-xxx` in [12-architecture-decisions.md](12-architecture-decisions.md).

---

## Document map

| File | Sections |
|---|---|
| [01-product.md](01-product.md) | Vision, problem, users, personas, journeys, NFRs, **A** Product architecture, **B** Exact MVP scope, **C** Deferred features |
| [02-data-model.md](02-data-model.md) | **D** Complete ERD, **E** Entities & relationships, **F** Blood-unit/component model |
| [03-workflows.md](03-workflows.md) | **G** Request lifecycle/state machine, **H** Donor mobilisation workflow, **I** Blood inventory workflow |
| [04-matching-and-notifications.md](04-matching-and-notifications.md) | **J** Matching engine, **K** Notification architecture |
| [05-security-and-access.md](05-security-and-access.md) | **L** Authentication & RBAC, **M** Permission matrix, **R** Security/privacy model |
| [06-api-specification.md](06-api-specification.md) | **N** API specification |
| [07-frontend-and-backend-structure.md](07-frontend-and-backend-structure.md) | **O** Frontend route map, **P** Backend module map |
| [08-audit-and-traceability.md](08-audit-and-traceability.md) | **Q** Audit & traceability model |
| [09-quality-and-operations.md](09-quality-and-operations.md) | **S** Testing, **T** Deployment, **U** Monitoring/logging, **V** Disaster recovery |
| [10-future-architecture.md](10-future-architecture.md) | **W** Mobile, **X** FHIR/HL7, **Y** AI/analytics |
| [11-risks-and-assumptions.md](11-risks-and-assumptions.md) | **Z** Risks & assumptions, **AA** Clinical/operational assumptions requiring validation, open questions |
| [12-architecture-decisions.md](12-architecture-decisions.md) | **AB** Architectural decisions & trade-offs (ADR log) |
| [13-delivery-plan.md](13-delivery-plan.md) | **AC** Feature dependency graph, **AD** Prioritized MVP backlog, **AE** Exact development order, **AF** Definition of Done |

Diagrams use Mermaid, which renders on GitHub, GitLab and most Markdown viewers.

---

## Executive summary

1. **What HemaNet is:** a blood-resource coordination network. It is not a donor-finder app.
   It runs two linked workflows (ADR-006):
   - **Fulfilment:** Hospital request → routed to a blood bank → units allocated from real, per-unit inventory → issued → received.
   - **Mobilisation:** a shortage (low stock or a request shortfall) → explainable donor matching → staff-approved donor appeal → donor response → appointment/collection **recorded by blood-bank staff** → processing → units become available.
2. **Inventory is per-unit** (ADR-004). Totals such as "O+ RBC: 14" are always calculated from unit records, never stored.
3. **Clinical rules are data, not code** (ADR-005). Compatibility, eligibility, component shelf life/storage and urgency levels live in versioned **rule sets** that follow the lifecycle DRAFT → PENDING_VALIDATION → VALIDATED → ACTIVE.
   The code only implements the *types* of rule; the *values* come from configuration. Pilot and production environments refuse to run clinical logic on unvalidated rule sets.
4. **Architecture:** a modular Flask monolith, a React/TypeScript SPA, and PostgreSQL. A job queue and outbox stored in Postgres mean MVP background work needs no Redis or broker. Deployment uses portable containers, because Kenyan data-residency rules may constrain hosting (AS-40).
5. **Privacy by default:** no patient identifiers in the MVP. Donor identities are hidden from hospitals, and from blood banks until the donor accepts an appeal. The system never stores infectious-disease test results.
6. **Deliberately deferred:** PostGIS, WebSockets, FHIR/HL7, ML, transfers, cold-chain, QR printing, mobile app, blockchain (rejected). Each has a named extension point.

## What I need from you

1. Approve, reject or amend the **[PROPOSED]** items. The highest-impact ones are summarised in `13-delivery-plan.md` §"Decisions needed from you".
2. Confirm the MVP scope in `01-product.md` §B.
3. Read the validation list in `11-risks-and-assumptions.md` §AA. It is effectively the agenda for your first stakeholder conversations.
