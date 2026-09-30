# 06 — N. API Specification (v1)

The machine-readable OpenAPI 3.1 document will be **generated from code** (flask-smorest, ADR-014) and published at `/api/v1/openapi.json` in non-production environments. This file is the design contract that the implementation must satisfy.

## N.1 Conventions [PROPOSED]
| Topic | Rule |
|---|---|
| Base path | `/api/v1`. Breaking changes → `/api/v2`, with v1 kept for at least 6 months once mobile clients exist |
| Format | JSON, UTF-8, `snake_case` fields, ISO-8601 UTC timestamps (`2026-09-30T14:05:00Z`), UUID string IDs |
| Auth | `Authorization: Bearer <access_token>` unless marked **public** |
| Success envelope | Single resource: the object itself. Lists: `{"data": [...], "page": {"next_cursor": "...", "limit": 25}}` |
| Pagination | Cursor-based (`?limit=25&cursor=…`), default 25, max 100 |
| Filtering/sorting | Explicit, allow-listed query params (`?status=SUBMITTED&sort=-created_at`); unknown params → 400 |
| Concurrency | Mutable resources return `version`; updates send `If-Match: "<version>"` → 409 `VERSION_CONFLICT` if stale |
| Idempotency | `Idempotency-Key` header **required** on: create request, reserve, issue, record donation, register units, launch appeal/wave, appeal response. Replays return the original response for 24 h |
| Tracing | Every response has `X-Request-ID` (echoed if supplied by the client and valid) |
| Rate limits | 429 with `Retry-After` |
| Time | Server time is authoritative; clients never send `created_at`/status timestamps |

### Error format
```json
{
  "error": {
    "code": "INVALID_STATE_TRANSITION",
    "message": "Request cannot be cancelled after units have been issued.",
    "details": [{"field": "status", "issue": "ISSUED"}],
    "request_id": "01J…"
  }
}
```
| HTTP | code(s) |
|---|---|
| 400 | `VALIDATION_ERROR`, `UNKNOWN_FIELD`, `MALFORMED_REQUEST` |
| 401 | `UNAUTHENTICATED`, `TOKEN_EXPIRED`, `MFA_REQUIRED` |
| 403 | `FORBIDDEN` (in-scope resource, missing permission), `FACILITY_NOT_VERIFIED`, `STEP_UP_REQUIRED` |
| 404 | `NOT_FOUND` (also used for out-of-scope resources) |
| 409 | `CONFLICT`, `VERSION_CONFLICT`, `INVALID_STATE_TRANSITION`, `UNIT_UNAVAILABLE`, `DUPLICATE_UNIT_IDENTIFIER`, `IDEMPOTENCY_KEY_REUSED` |
| 422 | `BUSINESS_RULE_VIOLATION` (e.g., `INCOMPATIBLE_UNIT`, `NO_ACTIVE_VALIDATED_RULE_SET`, `SUPPLIER_NOT_LINKED`) |
| 429 | `RATE_LIMITED` |
| 500/503 | `INTERNAL_ERROR`, `SERVICE_UNAVAILABLE` |

## N.2 Endpoint catalogue
Permission codes refer to §M. "Scope" says which facility the permission is checked against.

### Auth & account
| Method & path | Purpose | Auth / permission |
|---|---|---|
| POST `/auth/register/donor` | Create donor user + profile; sends phone OTP | public; rate-limited |
| POST `/auth/register/facility` | Create user + facility (PENDING) + founding membership | public; rate-limited |
| POST `/auth/login` | → `{access_token, expires_in, mfa_required?}` + refresh cookie | public |
| POST `/auth/mfa/verify` | Complete login with TOTP/recovery code | partial token |
| POST `/auth/token/refresh` | Rotate refresh token, new access token | refresh cookie + CSRF header |
| POST `/auth/logout` | Revoke the current refresh family | refresh cookie + CSRF |
| POST `/auth/phone/send-code`, `/auth/phone/verify` | Phone OTP | authenticated (or registration context) |
| POST `/auth/email/verify` | Consume email token | public (token) |
| POST `/auth/password/forgot`, `/auth/password/reset` | Reset flow | public; enumeration-safe |
| POST `/auth/invitations/accept` | Staff accepts invite code, sets password | public (code) |
| POST `/auth/mfa/totp/enroll`, `/auth/mfa/totp/confirm`, DELETE `/auth/mfa/totp` | MFA management | self (+step-up for removal) |
| POST `/auth/step-up` | Re-verify MFA for sensitive actions | self |
| GET `/me` · PATCH `/me` | Profile (name, language, email change → re-verify) | self |
| GET `/me/memberships` | Facilities + roles + permissions (for UI rendering only) | self |
| GET `/me/sessions` · DELETE `/me/sessions/{session_id}` | Session management | self |
| POST `/me/data-export` · POST `/me/deactivate` | Data-subject rights | self [VALIDATE AS-42] |

### Reference data
| Method & path | Purpose | Auth |
|---|---|---|
| GET `/reference/counties` (`?include=sub_counties`) | Counties/sub-counties | public |
| GET `/reference/blood-components` | Active components | authenticated |
| GET `/reference/urgency-levels` | From ACTIVE URGENCY rule set | authenticated |
| GET `/reference/reason-codes?category=` | Controlled reasons | authenticated |
| GET `/reference/rule-sets/active` | Active rule-set IDs, versions, validation status (drives the "unvalidated rules" banner) | authenticated |

### Donors (self-service)
| Method & path | Purpose | Permission |
|---|---|---|
| GET/PATCH `/me/donor-profile` | View/update profile (blood group editable only while SELF_REPORTED) | `donor_profile.manage_own` |
| PUT `/me/donor-profile/availability` | `{availability, unavailable_until}` | same |
| GET/PUT `/me/notification-preferences` | Channels, quiet hours, cap | same |
| GET `/me/eligibility` | Evaluated now → 3-state + reasons + next date + rule-set status | `donor.eligibility.view_own` |
| GET `/me/donations` | Own donation history (date, site, outcome) | same |
| GET `/me/appeals` | Appeals the donor was invited to (active first) | `appeal.respond` |
| GET `/me/appeals/{appeal_id}` | Details: site, window, slots, group needed | same |
| POST `/me/appeals/{appeal_id}/response` | `{response: ACCEPTED|DECLINED, slot_start?, decline_reason_code?}` | same; Idempotency-Key |
| GET `/me/appointments` · POST `/me/appointments/{id}/cancel` | Own appointments | same |
| GET `/appeal-links/{token}` | Resolve a signed link → minimal appeal info + donor first name | public (token) |
| POST `/appeal-links/{token}/response` | Respond without login | public (token); single-use per response type |

### Donors (staff)
| Method & path | Purpose | Permission (scope) |
|---|---|---|
| POST `/donors/lookup` | Body `{phone_e164}` or `{donor_reference}` → exact match only, minimal fields; audited (POST keeps identifiers out of URLs/logs) | `donor.lookup` (acting facility) |
| POST `/donors/{donor_id}/blood-group-confirmation` | Set LAB_CONFIRMED ABO/Rh | `donor.blood_group.confirm` |
| POST `/donors/{donor_id}/deferrals` · POST `/deferrals/{id}/lift` | Record/lift a deferral (category code only) | `donor.deferral.record` |
| GET `/donors/{donor_id}/eligibility?facility_id=` | Staff view at check-in (snapshot saved) | `donation.record` |

### Donations
| Method & path | Purpose | Permission |
|---|---|---|
| POST `/donations` | `{facility_id, donor_id, collected_at, outcome, donation_type, donation_identification_number?, appointment_id?}` | `donation.record` @ facility; Idempotency-Key |
| GET `/donations?facility_id=&from=&to=&outcome=` | Facility donation list | `donation.view` @ facility |
| GET `/donations/{id}` | Detail incl. derived units | same |

### Facilities & admin
| Method & path | Purpose | Permission |
|---|---|---|
| GET `/facilities?capability=&county_id=&q=` | Directory of VERIFIED facilities (public fields) | authenticated |
| GET `/facilities/{id}` · PATCH `/facilities/{id}` | Detail / update profile | read: authenticated; write `facility.update_profile` |
| GET `/facilities/{id}/memberships` · POST (invite) · PATCH `/facilities/{id}/memberships/{mid}` (role/status) | Staff management | `facility.membership.manage` |
| GET/POST `/facilities/{id}/storage-locations` · PATCH `…/{loc_id}` | Storage locations | `storage_location.manage` |
| GET `/facilities/{id}/supply-links` | Suppliers of a hospital / hospitals served by a bank | member of facility |
| GET `/admin/facilities?verification_status=` | Verification queue | PLATFORM_ADMIN |
| POST `/admin/facilities/{id}/verification` | `{decision, method, evidence_reference, notes}` | `facility.verify` (step-up) |
| POST `/admin/supply-links` · PATCH `/admin/supply-links/{id}` | Manage links | `supply_link.manage` |
| GET `/admin/users?q=&status=` · POST `/admin/users/{id}/suspend` · `/reactivate` | User administration | `user.suspend` (step-up) |
| POST `/admin/users/{id}/platform-roles` · DELETE `…/{role_code}` | Grant/revoke platform roles | `platform_role.grant` (step-up) |

### Clinical configuration
| Method & path | Purpose | Permission |
|---|---|---|
| GET `/admin/rule-sets?domain=&status=` · GET `/admin/rule-sets/{id}` | List/detail with entries | `rule_set.view` |
| POST `/admin/rule-sets` | New DRAFT (optionally cloned from an existing set) | `rule_set.draft_edit` |
| PUT `/admin/rule-sets/{id}/entries` | Replace entries (DRAFT only; validated per domain schema) | `rule_set.draft_edit` |
| POST `/admin/rule-sets/{id}/submit` | DRAFT → PENDING_VALIDATION (entries frozen) | `rule_set.draft_edit` |
| POST `/admin/rule-sets/{id}/validation` | Record validator name/role/org/source/date → VALIDATED | `rule_set.record_validation` (step-up) |
| POST `/admin/rule-sets/{id}/activate` | VALIDATED → ACTIVE; previous ACTIVE → RETIRED (one transaction) | `rule_set.activate` (step-up) |
| GET `/admin/rule-sets/{id}/diff?against=` | Entry-level diff between versions | `rule_set.view` |

### Inventory
| Method & path | Purpose | Permission |
|---|---|---|
| GET `/inventory/units?facility_id=&status=&component=&abo=&rh=&expires_before=&q=` | Unit list | `inventory.view_units` @ facility |
| POST `/inventory/units` | Register one unit | `unit.register` / `unit.register_released`; Idempotency-Key |
| POST `/inventory/units/bulk` | ≤ 200 units, atomic; response has per-row errors on failure | same |
| POST `/inventory/units/import/validate` | CSV dry-run → row report | same |
| GET `/inventory/units/{id}` · GET `/inventory/units/{id}/events` | Detail + chain of custody | `inventory.view_units` |
| POST `/inventory/units/{id}/release` · `/quarantine` · `/discard` · `/correct` | Status actions (reason codes where required) | `unit.release` / `unit.quarantine` / `unit.discard` / `unit.correct` |
| GET `/inventory/availability?facility_id=` | Derived counts | `inventory.view_units` |
| GET `/inventory/network-availability?requesting_facility_id=&component=&abo=&rh=` | Aggregates across linked suppliers, with `last_change` | `inventory.view_network_availability` |
| GET `/inventory/expiring?facility_id=&within_hours=` | Expiring soon | `inventory.view_units` |
| GET/PUT `/inventory/thresholds?facility_id=` | Low-stock thresholds | view: `inventory.view_units`; write: `stock_threshold.manage` |
| POST `/inventory/stock-takes` · PUT `/inventory/stock-takes/{id}/items` · POST `/inventory/stock-takes/{id}/complete` | Reconciliation | `stock_take.perform` / `.approve` |

### Blood requests & fulfilment
| Method & path | Purpose | Permission |
|---|---|---|
| POST `/blood-requests` | Create + route (body below) | `blood_request.create` @ requesting facility; Idempotency-Key |
| GET `/blood-requests?facility_id=&perspective=requesting|supplying&status=&urgency=&sort=` | Queue/list | `blood_request.view` |
| GET `/blood-requests/{id}` | Detail with derived counts, current routing, allowed actions | `blood_request.view` |
| GET `/blood-requests/{id}/timeline` | Status history + key events | same |
| POST `/blood-requests/{id}/routing` | Re-route after decline `{supplier_facility_id}` | `blood_request.route` |
| POST `/blood-requests/{id}/routing/accept` · `/routing/decline` | Supplier response | `blood_request.respond` @ supplier |
| GET `/blood-requests/{id}/allocation-suggestions` | Inventory matcher output with explanations and `shortfall` | `allocation.manage` @ supplier |
| POST `/blood-requests/{id}/allocations` | Reserve `{unit_ids[], confirm_conditional?}` | `allocation.manage`; Idempotency-Key |
| POST `/allocations/{id}/release` | Release a reservation `{reason_code}` | `allocation.manage` |
| POST `/blood-requests/{id}/issue` | Issue `{allocation_ids[]}` | `allocation.issue`; Idempotency-Key |
| POST `/blood-requests/{id}/receipts` | Hospital confirms receipt `{allocation_ids[]}` | `blood_request.receive` |
| POST `/blood-requests/{id}/cancel` · `/close` | `{reason_code, note?}` | `blood_request.cancel` / `.close` |
| POST `/blood-requests/{id}/appeal` | Create a DRAFT appeal prefilled from the shortfall | `appeal.manage` @ supplier |

Example: create request
```http
POST /api/v1/blood-requests
Idempotency-Key: 7c1e…
{
  "requesting_facility_id": "…",
  "supplier_facility_id": "…",
  "component_code": "RBC",
  "abo": "O", "rh": "POS",
  "units_requested": 2,
  "urgency_code": "URGENT",
  "required_by": "2026-09-30T18:00:00Z",
  "external_reference": "LAB-4471",
  "notes": null
}
→ 201
{
  "id": "…", "reference_code": "REQ-2026-000123", "status": "SUBMITTED", "version": 1,
  "units": {"requested": 2, "reserved": 0, "issued": 0, "received": 0},
  "urgency": {"code": "URGENT", "display_name": "Urgent", "rule_set_status": "VALIDATED"},
  "routing": {"supplier": {"id": "…", "name": "…"}, "status": "PENDING", "routed_at": "…"},
  "allowed_actions": ["cancel"],
  "created_at": "…"
}
```
`allowed_actions` is computed server-side from permissions and state. The UI uses it to show buttons, and the server still re-checks every action.

### Mobilisation
| Method & path | Purpose | Permission |
|---|---|---|
| GET `/appeals?facility_id=&status=` | List (incl. SUGGESTED) | `appeal.view` |
| POST `/appeals` | Create DRAFT (manual) | `appeal.manage` |
| GET `/appeals/{id}` · PATCH `/appeals/{id}` | Detail / edit DRAFT or SUGGESTED | `appeal.view` / `appeal.manage` |
| GET `/appeals/{id}/target-group-suggestions` | Groups suggested from ACTIVE compatibility rule set | `appeal.manage` |
| POST `/appeals/{id}/preview` | Run matcher (no contact) → masked ranked candidates + explanations + counts | `appeal.manage` |
| POST `/appeals/{id}/waves` | Launch next wave `{size}` | `appeal.manage`; step-up not required; Idempotency-Key |
| POST `/appeals/{id}/pause` · `/resume` · `/close` · `/cancel` | Lifecycle | `appeal.manage` |
| GET `/appeals/{id}/candidates?wave=&response=` | Masked, or revealed if ACCEPTED | `appeal.view_candidates` |
| GET `/appeals/{id}/summary` | Counts only (hospital view) | `appeal.view` |
| GET `/appointments?facility_id=&date=` | Day list at collection site | `appointment.check_in` |
| POST `/appointments/{id}/check-in` · `/no-show` | Staff actions | `appointment.check_in` |

### Notifications
| Method & path | Purpose | Permission |
|---|---|---|
| GET `/me/notifications?unread=true` | In-app inbox | self |
| POST `/me/notifications/{id}/read` · POST `/me/notifications/read-all` | Mark read | self |
| GET `/me/notifications/unread-count` | Cheap polling endpoint | self |
| GET `/admin/notification-deliveries?status=&channel=&from=` | Delivery health | `notification.delivery_admin` |
| POST `/admin/notification-deliveries/{id}/retry` | Manual retry | same |
| POST `/webhooks/sms/{provider}` · `/webhooks/email/{provider}` | Delivery reports | provider signature |

### Reports, audit, ops
| Method & path | Purpose | Permission |
|---|---|---|
| GET `/reports/donation-trends?facility_id=&from=&to=&granularity=week` | [CONFIRMED] | `report.view` |
| GET `/reports/shortages?…` | Threshold breaches, unfulfilled/partial requests | `report.view` |
| GET `/reports/donor-activity?…` | Appeals, contacts, acceptance/show-up/donation conversion (aggregate) | `report.view` |
| GET `/reports/request-performance?…` | Time to accept/issue/complete (median, p90), fulfilment rate | `report.view` |
| GET `/reports/wastage?…` | Expired/discarded vs issued, by component | `report.view` |
| GET `/reports/{name}.csv?…` | CSV export (streamed; audited) | `report.view` |
| GET `/admin/audit-events?entity_type=&entity_id=&actor_id=&action=&from=&to=` | Audit viewer | `audit.view` |
| GET `/admin/audit-events/verify-chain?from_id=&to_id=` | Hash-chain verification | PLATFORM_ADMIN |
| GET `/healthz` (liveness) · GET `/readyz` (DB + migrations at head + worker heartbeat fresh) | Ops | public (no details) / internal network |

## N.3 Real-time strategy (MVP) [PROPOSED, ADR-012]
Polling with TanStack Query `refetchInterval`: 15 s for request queues and request detail when non-terminal; 30 s for notification unread count; 60 s for inventory dashboards; paused when the tab is hidden. The endpoints are cheap, indexed queries. Upgrade path: Server-Sent Events fed by outbox events (V1), with the same query keys invalidated on push.
