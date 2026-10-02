# ADR-020 — Application-generated UUIDv7

- **Type:** Technical/tooling decision. It refines ADR-016 within the approved
  architecture and doesn't change it.
- **Status:** Accepted
- **Date:** 2026-10-02
- **Phase:** E1a (backend foundation)

- **Decision:** UUID primary keys are UUIDv7 (RFC 9562 §5.7), generated in the
  application by `app.core.ids` (`new_id()`). The generator is thread-safe and
  monotonic per process (RFC 9562 §6.2, Method 1: a 12-bit counter in `rand_a`
  seeded randomly each millisecond, borrowing the next millisecond on overflow, never
  going backwards when the wall clock does). No third-party dependency.
- **Context:** The blueprint (§E) asks for "uuid v7 where available, else v4". Python
  3.13 has no `uuid.uuid7()` (added in 3.14) and PostgreSQL 16 has no `uuidv7()`
  (added in 18).
- **Alternatives:** UUIDv4 (random inserts fragment B-tree indexes); a third-party
  package (a dependency for about 40 lines of code); ULIDs (not UUIDs, needing a
  separate column type).
- **Reason:** Time-ordered keys keep indexes compact at the pilot's insert volumes,
  while staying non-enumerable for IDOR defence (ADR-016).
- **Consequences:**
  - All callers use `new_id()`, so the implementation can be swapped for
    `uuid.uuid7()` or a database default once the platforms support it, without
    changing call sites.
  - Id ordering is an implementation property, **not a business rule**: ids from
    different processes interleave, and code must sort by explicit timestamps
    (with id only as a tie-breaker).
  - The embedded timestamp reveals creation time to within a millisecond. That's
    acceptable because records already expose `created_at`.
