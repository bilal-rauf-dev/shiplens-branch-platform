# 07 — Business Rules Catalogue

Enforcement points: **DB** = constraint/trigger · **SVC** = service layer (authoritative) · **FORM** = Django form validation (server) · **UI** = HTML attributes / hidden controls (convenience only).
All configurable values live in `BUSINESS_RULES` (settings) with an override row in `system_settings` (editable by Super Admin, audited). Shown as `{name=default}`.

## 1. Identifiers

| ID | Rule | Enforcement | Test |
|---|---|---|---|
| BR-001 | Branch code = `BR-{city.code}-{NN}`, NN = next per-city counter, zero-padded to 2 (grows to 3+ automatically). | SVC (counter table `id_sequences`, `SELECT … FOR UPDATE`), DB unique | `T-BRN-CODE-FORMAT`, `T-BRN-CODE-RACE` |
| BR-002 | Branch code is immutable and never reused (closed branches keep it). | SVC (field not in any form), DB trigger blocks UPDATE of `code` | `T-BRN-CODE-IMMUTABLE` |
| BR-003 | Member ID = `M-{YYYY}-{NNNNN}`, YYYY = Asia/Karachi year at acceptance, counter per year. | SVC counter, DB unique | `T-MEM-ID-FORMAT`, `T-MEM-ID-RACE` (10 threads accept 10 apps → 10 distinct sequential IDs) |
| BR-004 | Application ref = `APP-{YYYY}-{NNNNN}`; collection ref = `COL-{branchcode}-{NNNNN}`; transfer ref = `TRF-{branchcode}-{NNNN}`. | SVC counter, DB unique | `T-ID-REFS` |
| BR-005 | City code: exactly 3 uppercase ASCII letters, unique. | FORM regex `^[A-Z]{3}$`, DB unique + check | `T-CITY-CODE` |

## 2. Branches

| ID | Rule | Enforcement | Test |
|---|---|---|---|
| BR-010 | Transitions only per `06` §1 table. | SVC transition table | `T-BRN-TRANSITIONS` (all 4×4 pairs) |
| BR-011 | Close requires 0 unsent collections and 0 reports in SUBMITTED/RESUBMITTED/RETURNED. | SVC guard | `T-BRN-CLOSE-GUARD` |
| BR-012 | Branch name unique (case-insensitive) within city. | DB unique index on `(city_id, lower(name_en))` | `T-BRN-NAME-UNIQUE` |
| BR-013 | Public directory shows FORMING/ACTIVE/PAUSED only. | SVC selector `public_branches()` | `T-PUB-BRANCH-VISIBILITY` |
| BR-014 | Branch Lead/HR Lead can be assigned only to non-closed branches. | SVC | `T-ASSIGN-CLOSED` |

## 3. Applications (public form) — field-by-field validation

| ID | Field | Type / required | Rules | Error key |
|---|---|---|---|---|
| BR-040 | `full_name` | text, required | trim; collapse spaces; 3–100 chars; regex `^[\p{L}\p{M} .'\-]+$` (Unicode letters incl. Urdu; via `regex` module or explicit char classes) | `err.name_invalid` |
| BR-041 | `email` | email, required | Django `EmailValidator`; ≤ 254; lower-cased for storage/dedupe | `err.email_invalid` |
| BR-042 | `phone` | text, required | Pakistani mobile: accept `03XXXXXXXXX`, `+923XXXXXXXXX`, `923XXXXXXXXX`, spaces/dashes stripped; regex after normalising `^\+923\d{9}$`; stored E.164 `+923…` | `err.phone_invalid` |
| BR-043 | `date_of_birth` | date, required | not in future; age ≥ `{MIN_VOLUNTEER_AGE=16}` and ≤ 100 on submission date (PKT) | `err.age_range` |
| BR-044 | `guardian_consent` | checkbox | required iff age < 18 | `err.guardian_required` |
| BR-045 | `city` / `preferred_branch` | select, required | must be an existing branch with status ACTIVE or FORMING (re-checked server-side, not trusted from options) | `err.branch_unavailable` |
| BR-046 | `interests` | multi-select, required ≥ 1 | values ⊂ published Program slugs + "general"; max 5 | `err.interests_required` |
| BR-047 | `availability` | multi-select, required ≥ 1 | ⊂ {weekday_mornings, weekday_evenings, weekends} | `err.availability_required` |
| BR-048 | `motivation` | textarea, required | 20–1000 chars after trim; stored as plain text (escaped on output) | `err.motivation_length` |
| BR-049 | `preferred_language` | radio, required | ∈ {en, ur}; defaults to current UI locale | — |
| BR-050 | `privacy_consent` | checkbox, required | must be true; `consent_at` timestamp stored | `err.consent_required` |
| BR-051 | Spam: `website` honeypot (hidden, `tabindex=-1`, `autocomplete=off`) must be empty; signed form-render timestamp must be ≥ `{FORM_MIN_SECONDS=3}` old and ≤ 2 h; ≤ `{APPLY_RATE=5/h}` per IP (django-ratelimit, DB cache); CSRF token. Failing honeypot/time → fake success, no row, `application.spam_blocked` log. Rate limit → 429 page. | SVC + middleware | `T-APP-SPAM-HONEYPOT`, `-TIMING`, `-RATE` |
| BR-052 | Duplicate flag: normalised email or phone matches a PENDING application or a non-LEFT member → `possible_duplicate=true`, `duplicate_of` set. Response is identical either way. | SVC | `T-APP-DUP-FLAG`, `T-APP-NO-ENUM` |
| BR-053 | Decision only from PENDING; under row lock; decline reason 5–500 chars. | SVC + DB check (`status` enum) | `T-APP-TERMINAL`, `T-APP-ACCEPT-RACE` |
| BR-054 | Accept = one transaction: lock app → check PENDING → generate member ID → create member → link → set ACCEPTED → audit ×2. Any failure rolls back everything. | SVC `transaction.atomic` | `T-APP-ACCEPT-ATOMIC` (inject failure after member insert → no member, app still PENDING) |
| BR-055 | Member email unique among non-LEFT members (case-insensitive). | DB partial unique index | `T-MEM-EMAIL-UNIQUE` |

## 4. Members & teams

| ID | Rule | Enforcement | Test |
|---|---|---|---|
| BR-056 | Member's team must belong to member's branch. | SVC + FORM (choices filtered); DB composite FK `(team_id, branch_id)` → `teams(id, branch_id)` | `T-MEM-TEAM-BRANCH` |
| BR-057 | Team name unique per branch (case-insensitive). | DB unique index | `T-TEAM-UNIQUE` |
| BR-058 | Status transitions per `06` §6; `left_on` ≥ `joined_on`. | SVC + DB check | `T-MEM-STATUS` |
| BR-059 | Search: case-insensitive `icontains` on name/email/member_id, phone normalised digits match; filters AND-combined; results scoped. | SVC selector | `T-MEM-SEARCH-*` |

## 5. Collections & transfers

| ID | Rule | Enforcement | Test |
|---|---|---|---|
| BR-060 | `amount` > 0, ≤ `{MAX_COLLECTION=10,000,000}`, 2 decimal places max. | FORM + DB `CHECK (amount > 0)` | `T-COL-AMOUNT` |
| BR-061 | `method` ∈ {CASH, CHEQUE, BANK_DEPOSIT}. No online methods. | DB check | `T-COL-METHOD` |
| BR-062 | `collection_date` ∈ `[today_pkt − LOCK_DAYS, today_pkt]`. | FORM + SVC | `T-COL-DATE-RANGE` |
| BR-063 | `receipt_no` required, 1–30 chars `^[A-Za-z0-9\-/]+$`, unique per branch. | FORM + DB unique `(branch_id, receipt_no)` | `T-COL-RECEIPT-UNIQUE` |
| BR-064 | **Lock:** `is_locked = clock.now() ≥ created_at + {COLLECTION_LOCK_DAYS=7} days`. Locked ⇒ no edit, no void, by any role. | SVC (single `assert_editable()`), model `save()` guard, no admin | `T-COL-LOCK-BEFORE` (6d23h59m editable), `T-COL-LOCK-AT` (7d exactly locked), `T-COL-LOCK-AFTER`, `T-COL-LOCK-CONFIG` (set 3 → locks at 3d) |
| BR-065 | Week-closed: if a report for (branch, week of `collection_date`) is SUBMITTED/RESUBMITTED/APPROVED/LOCKED, create/edit/void with a date in that week is rejected. | SVC | `T-COL-WEEK-CLOSED` |
| BR-066 | Create only when branch ACTIVE. | SVC | `T-COL-BRANCH-ACTIVE` |
| BR-067 | (Should) Adjustment entry: `entry_type=ADJUSTMENT`, amount may be negative, requires `adjusts_collection_id` + reason, dated today; included in totals. | SVC + DB check `(entry_type='ADJUSTMENT' OR amount > 0)` | `T-COL-ADJUST` |
| BR-068 | Void: reason 5–300 chars; voided excluded from every total and from unsent list. | SVC | `T-COL-VOID` |
| BR-069 | Transfer: ≥ 1 collection; all same branch as transfer, not voided, not already sent; `transfer.total_amount` = Σ amounts (computed, stored); `transfer_date` ≤ today and ≥ max(collection_date). | SVC under `select_for_update` of chosen collections | `T-XFER-RULES`, `T-XFER-DOUBLE` |
| BR-070 | Sent collections are immutable. | SVC + trigger (reject UPDATE of amount/date/method when `transfer_id` not null) | `T-XFER-IMMUTABLE` |
| BR-071 | **Unsent (unrouted)** = `transfer_id IS NULL AND voided_at IS NULL`. Age = `today_pkt − collection_date` days. | SVC selector | `T-DASH-UNSENT` |

## 6. Weekly reports

| ID | Rule | Enforcement | Test |
|---|---|---|---|
| BR-080 | Week = Monday..Sunday in Asia/Karachi; `week_start` is a Monday. `{WEEK_START_DAY=MON}`. | DB `CHECK (extract(isodow from week_start)=1)` (relaxed if setting changes — documented) + SVC | `T-RPT-WEEK` |
| BR-081 | Unique report per (branch, week_start). | DB unique | `T-RPT-UNIQUE` |
| BR-082 | Draft creation idempotent (`get_or_create` inside transaction, unique constraint catches races). | SVC + DB | `T-RPT-AUTODRAFT-IDEMPOTENT` |
| BR-083 | Aggregates (for branch B, week W=[s,e]): `total_amount = Σ amount` of non-voided collections with `collection_date ∈ [s,e]`; `entry_count`; `by_method{CASH,CHEQUE,BANK_DEPOSIT}`; `unsent_amount_at_week_end` = Σ amount of those collections not sent by `e 23:59`; `new_members` = members with `joined_on ∈ [s,e]`; `active_members_end` = members ACTIVE with `joined_on ≤ e` (current status — documented approximation); `applications_received/accepted/declined` within [s,e]. | SVC `report_aggregates(branch, week)` | `T-RPT-AGGREGATES` |
| BR-084 | Narrative fields from `REPORT_FIELDS` registry: `activities` (required, 10–2000), `volunteer_hours` (int 0–10000, required), `issues` (optional ≤ 2000). | FORM generated from registry | `T-RPT-FIELD-REGISTRY` |
| BR-085 | Submit only after week end `{ALLOW_SUBMIT_CURRENT_WEEK=false}`. | SVC guard | `T-RPT-SUBMIT-EARLY` |
| BR-086 | On submit/resubmit: snapshot = aggregates + narrative + list of line items (collection id, ref, date, method, amount); `snapshot_hash = sha256(canonical_json)`. | SVC | `T-RPT-SNAPSHOT` |
| BR-087 | Return comment 5–1000 chars, required. | FORM + SVC | `T-RPT-RETURN-COMMENT` |
| BR-088 | Approve/return require `expected_revision == report.revision` and state ∈ {SUBMITTED, RESUBMITTED} (optimistic concurrency). | SVC under row lock | `T-RPT-CONCURRENT-REVIEW` |
| BR-089 | LOCKED report and its lines: any UPDATE/DELETE rejected. | DB trigger + SVC | `T-RPT-LOCKED-IMMUTABLE` (raw SQL update raises) |
| BR-090 | **Approved amount** for dashboard = Σ `weekly_report_lines.amount` of LOCKED reports (latest revision), never recomputed from collections. | SVC selector | `T-DASH-SEED` |

## 7. Dashboard formulas — see `09-dashboard-and-seed-data.md` (BR-100…BR-110).

## 8. Content

| ID | Rule | Enforcement | Test |
|---|---|---|---|
| BR-120 | Slug unique per type, `^[a-z0-9-]{3,80}$`, auto from EN title. | DB unique + FORM | `T-CMS-SLUG` |
| BR-121 | Publish requires EN title + body and UR title; UR body optional (falls back to EN with "English only" note). | SVC | `T-CMS-PUBLISH-GUARD` |
| BR-122 | Event: `end ≥ start`; past events shown under "Past" automatically. | FORM + DB check | `T-CMS-EVENT-DATES` |
| BR-123 | Body is Markdown → HTML via `markdown` then sanitised with `nh3` allow-list (p, h2–h4, ul, ol, li, a[href], strong, em, blockquote); links get `rel="noopener"`. | SVC on save + template filter | `T-SEC-XSS-CMS` |

## 9. Audit

| ID | Rule | Enforcement | Test |
|---|---|---|---|
| BR-130 | Every service mutation calls `audit.record(...)` inside the same `transaction.atomic`. | SVC + review checklist + coverage test | `T-AUD-COVERAGE`, `T-AUD-ATOMIC` |
| BR-131 | `audit_log` UPDATE/DELETE/TRUNCATE rejected. | DB trigger | `T-AUD-IMMUTABLE` |
| BR-132 | `hash = sha256(prev_hash ‖ canonical_json(row without hash))`; chain serialised by `pg_advisory_xact_lock(<audit key>)`. | SVC | `T-AUD-CHAIN` |
| BR-133 | Secrets/passwords never stored in `before/after` (deny-list of field names). | SVC | `T-AUD-REDACT` |

## 10. Time

| ID | Rule | Enforcement | Test |
|---|---|---|---|
| BR-140 | All timestamps stored UTC (`USE_TZ=True`); business dates computed in `TIME_ZONE='Asia/Karachi'` via `core.clock.today()`. | SVC | `T-CLOCK-PKT` (UTC 20:30 on Sunday = Monday 01:30 PKT → next week) |
| BR-141 | Code never calls `timezone.now()` directly in domain logic; uses `core.clock.now()` (patchable). | lint rule (ruff banned-api) | CI |
