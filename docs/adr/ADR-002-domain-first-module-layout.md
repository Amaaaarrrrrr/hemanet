# ADR-002 — Domain-first module layout

- **Status:** Accepted
- **Date:** 2026-09-30
- **Source:** [Blueprint §AB](../blueprint/12-architecture-decisions.md) (text carried over verbatim)

- **Decision:** `app/modules/<domain>/{models,schemas,repository,domain,service,policies,routes}` instead of layer-first top-level folders.
- **Alternatives:** The suggested hybrid layout (layers + domains side by side).
- **Reason:** Each feature lives in one place; ownership of models is clear; cross-module access only through services and events.
- **Consequences:** Some shared utilities live in `core/`; discipline is needed so `core` doesn't grow domain logic.
