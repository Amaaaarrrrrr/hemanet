# 11 — Risks, Assumptions, Clinical/Operational Validation

## Z. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | **No confirmed stakeholder access**: workflows are built on assumptions and don't match real practice | High | High | Validation list AA is the agenda for the first stakeholder meetings; rules and roles are configurable; build the foundation first, pilot-specific details last |
| R-02 | Unvalidated clinical rules used in a real setting | Medium | **Critical** | Rule-set lifecycle; `REQUIRE_VALIDATED_RULES` guard; UI banner; separation of duties; audit |
| R-03 | **Data-entry burden**: per-unit tracking costs staff time, so adoption fails or data goes stale | High | High | Scanner-friendly entry, bulk/CSV import, minimal required fields, measure time per task in usability tests; later integration with the blood service's existing systems |
| R-04 | Duplicate entry with an existing blood-establishment system (if one exists) | Medium | High | Ask early (AS-36); design import/export; favour integration over parallel entry in V1+ |
| R-05 | Stale availability misleads hospitals | Medium | High | Freshness indicators, "indicative" wording, requests still confirmed by the blood bank, stock-take reconciliation metrics |
| R-06 | Donor data breach (sensitive personal data) | Low–Medium | **Critical** | Minimisation, masking, RBAC, MFA, encryption, audit, DPIA, incident runbook |
| R-07 | Alert fatigue / donor burnout | Medium | Medium | Staff-launched appeals, caps, cooldown, fairness factor, opt-out respected |
| R-08 | SMS costs and delivery reliability in Kenya | Medium | Medium | Spend caps/alerts, provider abstraction, secondary provider, in-app fallback, delivery metrics |
| R-09 | Feature-phone donors can't use web links | High | Medium | Two-way SMS/USSD as a V1–V2 option; channel-agnostic response service; `STAFF_RECORDED` response channel (phone calls) |
| R-10 | Data-residency non-compliance from choice of hosting | Medium | High | Decide hosting after legal review (AS-40) and before pilot; portable containers |
| R-11 | Fake facilities or impersonation | Low | High | Verification workflow, KMHFL code, out-of-band confirmation, no operational access until verified |
| R-12 | Over-scoping: building V1–V3 features too early | Medium | High | MVP scope §B locked; each deferred item has an explicit extension point only |
| R-13 | Single-developer bus factor | Medium | Medium | ADRs, docs, tests, conventional structure |
| R-14 | Over-claiming (e.g., "clinically validated") | Medium | High | Language policy (master §48), prototype disclaimers in UI and docs |
| R-15 | Liability if HemaNet contributes to a delay or wrong product | Low | **Critical** | HemaNet never replaces the clinical cross-match/issue checks; it supports coordination only; legal review of terms; the pilot runs in parallel with existing processes |
| R-16 | Worker/job failure silently stops escalations or expiry | Low | High | Heartbeat alerts, query-time expiry filters (correctness doesn't depend on jobs), readiness checks |

## Assumptions (general)
- The PDF reflects the intended product. Your decisions of 2026-09-30 supersede it where they differ.
- Pilot scale: ≤ 20 facilities, ≤ 50k registered donors, ≤ 100k units per year (sizing only).
- Staff have at least intermittent internet access and a browser (desktop, tablet or phone) [VALIDATE AS-49].
- English is acceptable for staff UIs at MVP [VALIDATE AS-23].

## AA. Clinical and operational assumptions requiring validation

Each item names what we're assuming, why it matters, who should validate it, and how the design contains the risk. "Kenyan blood-service authority" means the national blood transfusion service or its current successor body. **Which institution now holds that mandate should itself be confirmed**, because we understand there have been recent institutional changes (AS-00).

| ID | Assumption | Why it matters | Validate with | Design containment |
|---|---|---|---|---|
| AS-00 | Identity of the current national authority for blood transfusion services and its guidelines | Every clinical rule depends on it | Ministry of Health / national blood service | All rules are configurable and cite a `validation_source_reference` |
| AS-01 | The problems P1–P5 exist and are priorities | Product-market fit | Hospital labs, blood banks | Discovery interviews before pilot |
| AS-02 | Supply structure: regional centres/satellites supply hospitals; some hospitals have their own blood banks | Facility model, routing | National blood service, hospital labs | Capability flags, not fixed types |
| AS-03 | Hospitals request from a known, limited set of suppliers; one supplier at a time | `supply_links`, routing | Same | Links are admin-managed data; multi-supplier routing is a future extension |
| AS-04 | Units received from an external centre arrive already tested and released, and may be registered as AVAILABLE | Registration path B | Blood bank managers | Separate permission `unit.register_released`; can be restricted |
| AS-05 | The workflow is request → accept → reserve → issue → receipt confirmation | State machine | Hospital labs + blood banks | States are code, but guards and permissions are configurable; receipt step can be made optional by config |
| AS-06 | Time-limited reservations are appropriate | Stock tied up vs availability | Blood bank managers | Hold time per urgency level (config) |
| AS-07 | No automatic component substitution | Allocation logic | Clinical/lab experts | Substitution is a future rule type |
| AS-08 | FEFO ordering is acceptable (no minimum remaining shelf life for certain patients) | Allocation suggestions | Clinical/lab experts | Suggestions only; staff choose; a min-shelf-life rule type can be added |
| AS-09 | Urgency levels, names, target and escalation times | Priority behaviour | Hospitals + blood service | URGENCY rule set |
| AS-10 | Escalation path: supplier manager → requester + platform admin | Response times | Same | Config + templates |
| AS-11 | **Blood group compatibility by component** (red cells, plasma, platelets, cryo) and preference ordering | Patient safety | National guidelines, transfusion medicine specialist | COMPATIBILITY rule set; deny-by-default; no built-in tables |
| AS-12 | **Donor eligibility** criteria: age limits, minimum inter-donation interval (possibly sex-specific), other criteria HemaNet should *not* assess | Donor safety; who gets contacted | National donor selection guidelines | DONOR_ELIGIBILITY rule set; 3-state output; screening at site is authoritative |
| AS-13 | Staff may record deferral *categories* in HemaNet, and doing so is appropriate and lawful | Sensitive data | Blood service + legal | Category codes only; can be disabled |
| AS-14 | HemaNet records only the release decision, not test results, and the right role releases units | Safety + privacy | Blood bank quality managers | Separate permission; results never stored |
| AS-15 | **Component shelf life and storage temperature ranges** | Expiry validation, future cold chain | National guidelines | COMPONENT_SPEC rule set; label expiry authoritative; mismatch = warning |
| AS-16 | Discard reason categories | Wastage analytics | Blood bank managers | `reason_codes` table |
| AS-17 | Which roles accept/decline requests, release units, issue units | RBAC | Facilities | Role→permission mapping is data |
| AS-18 | Whether family/replacement donation practices exist at pilot sites and how HemaNet should treat them | Mobilisation design; ethics | Hospitals + blood service | Appeals are facility-level (not patient-directed); patient-directed appeals are **not supported** until validated |
| AS-19 | Whether donor appeals linked to a specific hospital request are appropriate to disclose to donors (e.g., "needed for a request at Hospital X") | Privacy, coercion risk | Blood service + ethics | Default message names only the collection site and group needed |
| AS-20 | Appeals should be launched by staff, not automatically | Alert storms, cost | Blood bank managers | Suggested → staff launch; auto-launch can be a future opt-in |
| AS-21 | Donors whose status is "Requires review" may be invited with a caveat | Wasted trips vs reach | Blood bank managers | Per-appeal toggle, default off |
| AS-22 | Donors can respond via smartphone links; the feature-phone share is unknown | Reach | Donor survey/pilot data | `STAFF_RECORDED` channel; two-way SMS/USSD future |
| AS-23 | Language needs (English/Kiswahili) | Accessibility | Users | i18n scaffolding in MVP |
| AS-24 | Slot-based appointments suit collection sites (vs walk-in only) | Mobilisation | Collection sites | Slots optional; walk-ins supported |
| AS-25 | County-level fallback for donors without coordinates is useful | Reach | Blood banks | Toggle per appeal |
| AS-26 | Mapping from priority to channels, and whether night-time alerts are acceptable | Donor experience | Donors + blood service | Config |
| AS-27 | SMS sender ID registration, bulk-SMS and consent rules (Communications Authority; DPA direct-marketing rules) | Legal delivery | Legal + provider | Provider adapters; consent records |
| AS-30 | Facilities can realistically record per-unit data (barcode scanners available? label formats?) | Adoption (R-03) | Blood bank staff | Scanner/CSV entry; usability testing |
| AS-31 | Unit/donation identifier format (e.g., whether ISBT 128 is used) and uniqueness across issuing centres | Duplicate prevention, traceability | Blood service | `issuing_system` namespace; pluggable format validators |
| AS-32 | Stock-take practice and frequency | Reconciliation | Blood banks | Optional feature |
| AS-33 | How donors are identified at collection (national ID?) and whether HemaNet should store it | Duplicates vs privacy | Blood service + legal | Not stored in MVP; phone + DOB + `donor_reference` |
| AS-34 | Back-entry after downtime is acceptable (recorded vs occurred time) | Data integrity | Blood banks | Separate timestamps |
| AS-35 | Approvals needed before a pilot (MoH, blood service, county health departments, ethics review if research data is collected) | Legality of pilot | MoH / county / ethics committee | Pilot readiness checklist (AE step 22) |
| AS-36 | Existing systems at blood banks/hospitals (lab/blood-establishment systems, KHIS reporting duties) | Duplicate entry (R-04) | Facilities | Import/export first; integration later |
| AS-37 | Cost-recovery/fees for blood processing and how they affect the request workflow | Workflow, scope | Hospitals + blood service | Out of MVP scope; no billing entities |
| AS-40 | **Data residency**: whether Kenyan regulations require HemaNet's health-related data to be processed/stored in Kenya | Hosting choice | Data-protection counsel | Portable deployment (ADR-015); decide before pilot |
| AS-41 | DPA obligations: ODPC registration, DPIA, lawful basis/consent wording, retention periods, 72-hour breach notification | Legal operation | Counsel / ODPC guidance | Consent versioning, retention config, runbooks |
| AS-42 | Donor erasure vs traceability retention | Rights vs safety | Counsel + blood service | Pseudonymisation design |
| AS-43 | Whether and how donors may be told their donation was used | Retention, privacy | Blood service + ethics | Future; no patient data ever |
| AS-44 | Authoritative county/sub-county list and codes | Reference data | Official publications | Seed with source citation |
| AS-45 | Session lifetimes acceptable for shared ward computers | Security vs usability | Hospitals | Config per role |
| AS-46 | Kenyan interoperability standards (national FHIR profiles, KHIS/DHIS2, facility registry APIs) | Future integration | Digital Health Agency / MoH | Adapter layer only |
| AS-47 | Whether HemaNet must register or be certified under the Digital Health Act before handling health data | Legal operation | Counsel / Digital Health Agency | Pilot readiness checklist |
| AS-48 | Blood service centres have KMHFL codes | Facility verification | KMHFL | `kmhfl_code` nullable |
| AS-49 | Connectivity and devices at facilities | UX, offline needs | Site visits | Lightweight SPA; outage snapshot |
| AS-50 | A pre-pilot baseline (current response times, wastage) can be measured | Impact measurement | Pilot facilities | Baseline data collection plan |

## Open questions for you
1. Who will run HemaNet during the pilot (you, a university, an NGO, a partner facility)? This determines the data-controller role under the DPA.
2. Do you have a target county or region for the first pilot?
3. Budget constraints for hosting and SMS (they affect the hosting option and SMS strategy)?
4. Team: are you developing alone, or will others contribute (affects process and code-review setup)?
5. Should HemaNet eventually handle hospital-internal inventory (hospital blood banks), or only supplier inventory? The model supports both; the MVP UI assumes supplier-side blood banks and hospital blood banks behave the same.
