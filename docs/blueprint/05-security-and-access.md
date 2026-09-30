# 05 — Authentication, RBAC, Permissions, Security & Privacy

## L. Authentication and RBAC

### L.1 Authentication [PROPOSED, ADR-007]
| Element | Design |
|---|---|
| Credentials | Email **or** phone + password. Argon2id (argon2-cffi; memory ≥ 64 MiB, t=3, p=1, tuned on target hardware). Minimum length 10, checked against a breached/common-password list; no composition rules (NIST SP 800-63B) |
| Access token | JWT, 15 min, HS256 with a key from the secrets manager (RS256 when a second service needs to verify tokens). Claims: `sub`, `sid` (refresh family), `iat`, `exp`, `jti`, `ver` (the user's `token_version`, bumped on password change/suspension). **No roles in the token.** Permissions are loaded server-side per request (cached ≤ 60 s), so revocation takes effect immediately |
| Refresh token | Opaque 256-bit random value, stored hashed. Rotated on every use; reuse detection revokes the family. Lifetime: 12 h idle / 7 days absolute for staff; 30 days for donors [PROPOSED][VALIDATE AS-45] |
| Web transport | Access token held **in memory** (not localStorage). Refresh token in a `__Host-hemanet_rt` cookie: `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth` |
| CSRF | Only the refresh/logout endpoints use a cookie. They require an `X-CSRF-Token` header matching a double-submit cookie, and check `Origin`. All other endpoints use a Bearer header, so they aren't CSRF-exposed |
| Mobile (future) | The same endpoints return the refresh token in the body when `client_type=MOBILE`, for storage in secure OS storage |
| MFA | TOTP (RFC 6238), mandatory for PLATFORM_ADMIN and CLINICAL_CONFIG_APPROVER; optional for others; 10 single-use recovery codes. Sensitive actions (activating a rule set, verifying a facility, granting platform roles) require an MFA check in the last 15 min (step-up) |
| Phone verification | 6-digit OTP, 10-min expiry, max 5 attempts, resend throttled (60 s, max 5/hour/number) |
| Brute force | Per-identifier progressive delay after 5 failures; lockout 15 min after 10; per-IP limits at the edge. Uniform error "Invalid credentials" |
| Account enumeration | Registration and reset responses are identical whether or not the account exists (with the email/SMS side channel handled asynchronously) |
| Session management | `/me/sessions` lists refresh families; users can revoke them. Admin suspension revokes all sessions |

### L.2 Authorization model [CONFIRMED principle "role ≠ permission"; PROPOSED design, ADR-008]
```
User ──< user_platform_roles >── Role (scope PLATFORM) ──< role_permissions >── Permission
User ──< facility_memberships >── Role (scope FACILITY) @ Facility
```
**Policy check** = `can(user, permission, resource)`:
1. **Permission:** does the user hold the permission through a platform role, or a facility role in the *resource's owning facility*?
2. **Scope/ownership:** the resource's facility (or donor owner) must match the membership (or the user themselves).
3. **State:** the facility is VERIFIED, the membership is ACTIVE, the user is ACTIVE.
4. **Capability:** the facility has the capability that the action needs (e.g., `can_hold_inventory` for unit actions).

Enforcement points:
- A decorator `@require_permission("blood_request.create")` on every route. A CI test fails if any route lacks either this decorator or an explicit `@public` marker.
- **Scoped repositories:** list queries take a `Scope` object built from the caller's memberships. There's no un-scoped query method in facility repositories, so BOLA is structurally hard to introduce.
- Resources outside the caller's scope return **404** (not 403) to avoid revealing that they exist.

### L.3 Roles
| Role | Scope | Label |
|---|---|---|
| DONOR | PLATFORM (self) | [CONFIRMED] |
| HOSPITAL_REQUESTER | FACILITY | [CONFIRMED] "hospital staff" |
| HOSPITAL_ADMIN | FACILITY | [PROPOSED] |
| BLOOD_BANK_OFFICER | FACILITY | [CONFIRMED] "blood bank staff" |
| BLOOD_BANK_MANAGER | FACILITY | [PROPOSED] |
| PLATFORM_ADMIN | PLATFORM | [CONFIRMED] |
| CLINICAL_CONFIG_APPROVER | PLATFORM | [PROPOSED] (separation of duties for clinical rules) |
| AUDITOR (read-only audit + reports) | PLATFORM | [FUTURE] |

Which staff role may approve requests and release units is **[VALIDATE AS-17]**. Because roles map to permissions in data, changing that later is a data migration, not a code change.

### L.4 Facility onboarding
1. Self-registration creates the user (PENDING_VERIFICATION), the facility (PENDING) and a membership (HOSPITAL_ADMIN or BLOOD_BANK_MANAGER, status INVITED).
2. Admin verifies the facility, which activates the founding membership.
3. The facility admin/manager invites staff (email/SMS invite code). Staff set passwords and verify their phone, and the membership becomes ACTIVE.
4. Platform admins **cannot** create memberships inside facilities, except to recover a facility whose founding admin has left (audited, MFA step-up).

---

## M. Permission matrix

Legend: ✅ allowed · 🔸 own facility only · 👤 self only · ⚠ with step-up MFA · — denied

| Permission code | Donor | Hosp. Requester | Hosp. Admin | BB Officer | BB Manager | Platform Admin | Clinical Config Approver |
|---|---|---|---|---|---|---|---|
| `profile.read_update` | 👤 | 👤 | 👤 | 👤 | 👤 | 👤 | 👤 |
| `donor_profile.manage_own` | 👤 | — | — | — | — | — | — |
| `donor.eligibility.view_own` | 👤 | — | — | — | — | — | — |
| `donor.lookup` (exact phone/ID match to record donation) | — | — | — | 🔸 | 🔸 | — | — |
| `donor.blood_group.confirm` | — | — | — | 🔸 | 🔸 | — | — |
| `donor.deferral.record` | — | — | — | 🔸 | 🔸 | — | — |
| `donation.record` | — | — | — | 🔸 | 🔸 | — | — |
| `donation.view` | 👤 own history | — | — | 🔸 | 🔸 | ✅ (aggregate + audited detail) | — |
| `facility.update_profile` | — | — | 🔸 | — | 🔸 | ✅ | — |
| `facility.membership.manage` | — | — | 🔸 | — | 🔸 | ⚠ recovery only | — |
| `facility.verify` | — | — | — | — | — | ⚠ | — |
| `supply_link.manage` | — | — | — | — | — | ✅ | — |
| `storage_location.manage` | — | — | — | — | 🔸 | — | — |
| `stock_threshold.manage` | — | — | — | — | 🔸 | — | — |
| `inventory.view_units` | — | — | — | 🔸 | 🔸 | ✅ read | — |
| `inventory.view_network_availability` (aggregates of linked suppliers) | — | 🔸 | 🔸 | 🔸 | 🔸 | ✅ | — |
| `unit.register` (QUARANTINED) | — | — | — | 🔸 | 🔸 | — | — |
| `unit.register_released` | — | — | — | 🔸 [VALIDATE] | 🔸 | — | — |
| `unit.release` (quarantine → available) | — | — | — | 🔸 [VALIDATE AS-17] | 🔸 | — | — |
| `unit.discard` / `unit.quarantine` | — | — | — | 🔸 | 🔸 | — | — |
| `unit.correct` (immutable fields, with reason) | — | — | — | — | 🔸 | — | — |
| `stock_take.perform` / `.approve` | — | — | — | 🔸 / — | 🔸 / 🔸 | — | — |
| `blood_request.create` / `.cancel` / `.close` / `.route` | — | 🔸 | 🔸 | — | — | — | — |
| `blood_request.view` | — | 🔸 (requesting) | 🔸 | 🔸 (routed-to) | 🔸 | ✅ | — |
| `blood_request.receive` | — | 🔸 | 🔸 | — | — | — | — |
| `blood_request.respond` (accept/decline) | — | — | — | 🔸 [VALIDATE AS-17] | 🔸 | — | — |
| `allocation.manage` (reserve/release) | — | — | — | 🔸 | 🔸 | — | — |
| `allocation.issue` | — | — | — | 🔸 | 🔸 | — | — |
| `appeal.view` | — | status + counts for linked requests | same | 🔸 | 🔸 | ✅ | — |
| `appeal.manage` (edit, preview, launch, waves, close) | — | — | — | — | 🔸 | — | — |
| `appeal.view_candidates` (masked; revealed after acceptance) | — | — | — | 🔸 | 🔸 | — | — |
| `appeal.respond` | 👤 | — | — | — | — | — | — |
| `appointment.check_in` / `.no_show` | — | — | — | 🔸 | 🔸 | — | — |
| `notification.read_own` | 👤 | 👤 | 👤 | 👤 | 👤 | 👤 | 👤 |
| `notification.delivery_admin` | — | — | — | — | — | ✅ | — |
| `rule_set.view` | — | ✅ (active only) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `rule_set.draft_edit` | — | — | — | — | — | ✅ | ✅ |
| `rule_set.record_validation` | — | — | — | — | — | — | ⚠ |
| `rule_set.activate` | — | — | — | — | — | — | ⚠ (cannot activate a set they drafted, when > 1 approver exists) |
| `user.suspend` / `.reactivate` | — | — | — | — | — | ⚠ | — |
| `platform_role.grant` | — | — | — | — | — | ⚠ | — |
| `report.view` | — | 🔸 own facility | 🔸 | 🔸 | 🔸 | ✅ network | — |
| `audit.view` | — | — | — | — | 🔸 own facility events | ✅ | — |

The matrix is also the source for a **parametrised authorization test suite** (§S): every endpoint × every role × in-scope/out-of-scope resource.

---

## R. Security and privacy model

### R.1 Threat model summary (STRIDE-lite) [PROPOSED]
| Threat | Example | Controls |
|---|---|---|
| Spoofing | Fake hospital registers to see availability / create requests | Facility verification before any operational permission; KMHFL code; out-of-band verification; unverified facilities see nothing operational |
| Spoofing | Stolen staff credentials | MFA (admins now, staff V1), refresh-token reuse detection, new-sign-in notifications, session revocation |
| Tampering | Staff alters unit expiry or history | Immutable unit fields + correction events with reason; append-only `unit_events`/`audit_events` with DB-level UPDATE/DELETE revocation and a hash chain |
| Tampering | Client sends `eligible: true` or `status: COMPLETED` | Server derives all state; request schemas don't accept computed fields (unknown fields → 400) |
| Repudiation | "I didn't issue that unit" | Actor + timestamp on every event; audit hash chain |
| Info disclosure | IDOR on `/blood-requests/{id}` | Scoped repositories, 404 on out-of-scope, UUIDs, authz test matrix |
| Info disclosure | PHI in SMS/logs | No patient identifiers collected; template variable allow-lists; log redaction filter; PHI warning on free-text fields |
| Info disclosure | Donor locations exposed | Coordinates rounded to ~1 km; donors masked until acceptance; banded counts |
| DoS | SMS pumping via OTP endpoint (costly in Kenya) | Per-number/IP/global OTP limits, CAPTCHA fallback after thresholds [PROPOSED], daily SMS spend cap alarm |
| DoS | Alert storm to donors | Staff-launched appeals, one active appeal per target, contact caps, cooldown |
| Elevation | Officer grants self manager | Only HOSPITAL_ADMIN/BB_MANAGER manage memberships; users can't modify their own memberships; audited |
| Elevation | Unvalidated clinical rules activated | Two-role separation, MFA step-up, `REQUIRE_VALIDATED_RULES` guard, audit |

### R.2 Application security controls [PROPOSED]
- Input validation at the API boundary (marshmallow schemas, `unknown=RAISE`), plus DB constraints as the final guard.
- SQLAlchemy parameterised queries only. Raw SQL is allowed only in the repository layer with bound parameters (lint rule).
- Response schemas are explicit allow-lists (e.g., the user schema never serialises `password_hash`).
- Security headers: HSTS (1 year, preload once stable), a CSP with no `unsafe-inline` for scripts, `X-Content-Type-Options`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` (geolocation only on pages that need it), `frame-ancestors 'none'`.
- CORS: explicit allow-list of the web origin(s) per environment; no wildcard with credentials.
- Rate limiting: edge (reverse proxy) plus application-level for auth/OTP/webhooks (Flask-Limiter with Postgres-backed counters in the MVP, Redis if scaling needs it).
- Error responses: generic messages with a `request_id`; stack traces never leave the server.
- Dependency scanning (pip-audit, npm audit), SAST (bandit, semgrep), secret scanning (gitleaks) in CI; Renovate/Dependabot for updates.
- Secrets: `.env` locally (`.env.example` committed); AWS Secrets Manager/SSM in hosted environments; rotation procedure documented.
- Field-level encryption (AES-GCM, app-managed key): TOTP secrets. Future candidates: national ID numbers if ever needed.
- Transport: TLS 1.2+ everywhere, including app ↔ DB (`sslmode=verify-full`).

### R.3 Privacy model [PROPOSED][VALIDATE AS-40–AS-43 with legal counsel]
**Legal context (to be confirmed by counsel):** Kenya Data Protection Act 2019 and its 2021 regulations; health data is *sensitive personal data*. Likely obligations: registration with the Office of the Data Protection Commissioner (ODPC), a DPIA for high-risk processing, a lawful basis and consent records, data-subject rights, breach notification to the ODPC within 72 hours, and possible data-localisation requirements. Kenya's Digital Health Act 2023 may impose further obligations on digital health solutions. **None of this is legal advice. Every item needs confirmation.**

| Data class | Examples | Stored? | Who can see |
|---|---|---|---|
| Identity | name, phone, email, DOB | Yes (minimum) | self; blood bank staff only for accepted appeal donors, donation recording and lookups (audited) |
| Donor health-related | blood group, deferral *category*, eligibility result, donation dates | Yes (minimum; category codes, not clinical detail) | self; collection-site staff |
| Laboratory results | infectious markers, haemoglobin values | **No** | — |
| Patient data | patient name, ID, diagnosis | **No** (ADR-013) | — |
| Operational | requests, units, allocations | Yes | scoped facilities; admin |
| Location | facility exact; donor rounded ~1 km | Yes | donor: self; others see only distance bands |
| Audit | actor, action, entity | Yes | admin; facility manager for their own facility's events |
| Technical | IP address | Truncated/hashed only, 90-day retention | admin |

Data-minimisation decisions:
- DOB instead of age; sex collected only if a validated rule needs it; no national ID number in the MVP [VALIDATE AS-33: donor identity verification method].
- Donor precise location is never stored. The browser geolocation result is rounded client-side **and** server-side.
- Free-text fields are limited in length, carry PHI warnings, and are excluded from logs and notifications.

Data-subject rights [PROPOSED][VALIDATE AS-42]:
- Export: `GET /me/data-export` (JSON) is generated as a job.
- Deletion: the donor account is deactivated and identity fields are pseudonymised after a retention period. **Donation and unit records are kept (linked to a pseudonymous ID)** because traceability retention obligations may apply. That conflict needs a legal and blood-service ruling.

Retention (placeholders to validate): notifications 12 months; login attempts 30 days; audit events ≥ 7 years [VALIDATE]; unit/donation records per blood-service retention rules [VALIDATE].

Data residency: see AS-40 and ADR-015. **Hosting location must be decided before the pilot, not after.**
