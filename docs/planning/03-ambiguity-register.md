# 03 — Ambiguity & Gap Register

Format per item: **Question · Why it matters · Options · Recommended default · Impact if wrong.**
Defaults are applied throughout the plan and collected as `ASSUMPTION-nn` in `21-assumptions-and-open-questions.md`.

---

### AMB-01 Deadline and task-open conflict — ✅ RESOLVED: 2 Nov 2026 23:59 PKT (user confirmation, 24 Oct)
- **Q:** Is the deadline 26 Oct 23:59 PKT (Overview) or 2 Nov 23:59 (sidebar)? Task opens 12 Oct or 19 Oct?
- **Why:** The 7-commit-day rule cannot be met by 26 Oct when starting on 24 Oct.
- **Options:** (a) assume 2 Nov; (b) assume 26 Oct; (c) ask.
- **Default:** Plan A = **2 Nov** (sidebar dates are internally consistent: open + 14 days, results +14 days); ask organisers today; commit daily from today either way. Open date is moot: our first commit is 24 Oct, later than both.
- **Impact if wrong:** If 26 Oct is final, the submission fails the commit-history gate regardless of quality. Plan B (26 Oct scope) salvages a working product for feedback/certificate eligibility only if organisers accept it.

### AMB-02 "Expected values" and the sample data
- **Q:** What sample data and expected dashboard values will judges use? The Overview says sample data and brand material are released when the task opens; I have not received them.
- **Why:** Gate 1 is pass/fail on exact values.
- **Options:** (a) wait; (b) design own deterministic seed + tolerant importer; (c) both.
- **Default:** (c). Build `seed_demo` (deterministic, values in `09-…` §4) **and** `import_sample_data <file>` accepting CSV/XLSX with a header-mapping YAML (`config/sample_mapping.yaml`) so column names/orders can be remapped without code. Dashboard has a **period selector** and an `as_of` date so values for a fixed reference period are reproducible. **Action: download the sample data/brand pack from the event page's Instructions/Submissions tab today and send it to me.**
- **Impact if wrong:** If judges load *their* file and our importer can't map it, G1 fails → reject. Mitigation: importer reports unmapped columns clearly; expected-value test regenerated from their file within ~2 h.
- **UPDATE 2026-10-24:** the entrant checked the event page and found **no sample data published**. Decision: **we author the sample data ourselves** and ship it as plain CSV files in `sample_data/` (branches, users, members, applications, collections, transfers, reports). `seed_demo` = `import_sample_data sample_data/` (one code path, so "when the sample data is loaded" is literally true). Expected dashboard values are published in README and asserted by `T-DASH-SEED`. A written question goes on the event's Discussion tab (public record) asking whether official data will be released; if it ever is, the same importer + mapping YAML loads it. README states: "No official sample data was provided; this fictional dataset was authored for the submission."

### AMB-03 Surprise twist task (5 pts)
- **Q:** What will it be? (Revealed later.)
- **Default:** Design for change (see `20-risks.md` §Twist-readiness). Likely categories and mitigations:

| Likely twist | Mitigation already in design | Est. effort |
|---|---|---|
| New role (e.g. "Auditor" read-only, "Regional Lead" multi-branch) | Single `PERMISSIONS` matrix + role enum + scope function; assignments already many-to-many; matrix test auto-expands. | 1–2 h |
| New report field (e.g. volunteer hours, beneficiaries served) | `REPORT_FIELDS` registry, values in JSONB `narrative`; snapshot stores whatever is registered. | 0.5–1 h |
| New workflow state (e.g. "Escalated", two-step approval) | Transition tables per entity; audit derives event names from table. | 1–3 h |
| Rule change (lock 7→3 days, week starts Sat) | `system_settings` / `settings.BUSINESS_RULES`; lock is computed, not stored. | 0.5 h |
| New export (Excel, monthly branch statement) | Exporter interface `rows(queryset) → columns + rows`, CSV/PDF renderers generic. | 1–2 h |
| New language (e.g. Punjabi/Sindhi) | Django `.po` per locale; CMS translation table keyed by locale; `LANGUAGES` list; bidi flag automatic. | 1–2 h + translation |
| New public page / CMS type | Content `type` enum + template per type. | 1 h |
| New KPI or dashboard filter | KPI functions isolated in `dashboard/kpis.py`, each with test. | 1 h |
| Notification (email on return/approval) | Domain events emitted in services → one hook point. Console email backend. | 2 h |
| Bulk import of members from Excel | Importer framework already exists for sample data. | 2–3 h |

- **Impact if wrong:** Up to 5 pts; low impact on gates.

### AMB-04 Collection 7-day lock semantics
- **Q:** 7 days from creation or from the collection date? Timezone? Can Super Admin unlock? Audited? Edits and deletes?
- **Options:** from `collection_date` (user-entered, can be manipulated by backdating) vs from `created_at` (server-controlled).
- **Default:** **Lock at `created_at + LOCK_DAYS` (7 × 24 h, exact instant, UTC stored, displayed Asia/Karachi).** Lock covers edit **and** void (no hard delete exists at all). **No unlock** by anyone — immutability is the point; corrections are made by an *adjustment entry* (Should-have, BR-067). Lock is **computed**, not stored, so no scheduler is needed and a rule change takes effect instantly. Additionally `collection_date` must be within `[today − LOCK_DAYS, today]` (local date) so backdating cannot smuggle entries into old weeks. Lock events are not audited (they are not changes); attempts to edit locked entries are rejected and logged as `collection.edit_denied`.
- **Impact if wrong:** If judges expect lock from collection date, behaviour differs by ≤ a few days for typical entries; switching is a one-line change in `Collection.lock_at` (keep it a single property).

### AMB-05 "Collections not yet sent to the main account" = "unrouted collections"
- **Q:** How is "sent" modelled? Who marks it? Partial transfers? Relation to lock/approval?
- **Default:** A **Transfer** record (branch, transfer date, bank/slip reference, note) created by **Branch Lead**, selecting one or more whole unsent, non-voided collections of their branch; the transfer total = sum of selected amounts. A collection is **unsent/unrouted** iff `transfer_id IS NULL AND voided_at IS NULL`. **No partial transfers** (split by recording two collections). Independent of lock and approval: a locked collection can still be unsent (shown with a red "locked, unsent" flag); marking sent makes it immutable even if within 7 days. Finance Reviewer *confirming* receipt is an optional enhancement (OPT-04).
- **Impact if wrong:** If judges expect Finance to mark sent, change one permission row and button placement (30 min).

### AMB-06 "Drafted automatically"
- **Q:** Scheduler or lazy? Week boundary? What does it aggregate? Render free tier sleeps.
- **Default:** ISO week **Monday 00:00 – Sunday 23:59 Asia/Karachi**. Drafts are created **lazily and idempotently** (`get_or_create(branch, week_start)`) when (a) a Branch Lead opens the Reports page (drafts for the current week and any past week since branch activation without a report), (b) the dashboard computes compliance, (c) `manage.py generate_weekly_drafts` runs (callable from a GitHub Actions scheduled workflow via a token-protected endpoint — optional). Render cron jobs are paid, so we don't rely on them. Draft figures are **computed live** until submission (no stale numbers); submission takes a snapshot.
- Aggregates: total amount, entry count, amount by method, unsent amount at week end, new members joined, active members at week end, applications received/accepted/declined. Manual fields: activities summary, volunteer hours, issues/needs.
- **Impact if wrong:** Low; a cron trigger can be added without changing the model.

### AMB-07 Report editing rights after return / after approval
- **Default:** Finance Reviewer **cannot edit figures**; only approve or return with mandatory comment. A Returned report reopens its week: Branch Lead may fix underlying collections (subject to the 7-day lock) and narrative fields, then resubmit (revision +1, new snapshot). After approval the week is closed: no collection can be created/edited with a date in that week. Corrections after approval → adjustment entry in the current week referencing the original (Should).
- **Impact if wrong:** Medium for G2 interpretation; the gate sequence itself is satisfied.

### AMB-08 Role scope
- **Default:**
  - Super Admin: global; administers users, branches, settings, audit; **cannot** approve reports or decide applications (segregation of duties) — but can view everything.
  - Finance Reviewer: global read of collections, transfers, reports, dashboard; approve/return; exports. No PII of applicants/members (sees counts).
  - Content Editor: CMS only; no operational data.
  - Branch Lead: scoped to assigned branches (normally exactly one).
  - HR Lead: scoped to assigned branches (one or more). Not global.
  - Only Super Admin creates users and branches.
- **Impact if wrong:** Matrix change = data change + test auto-regenerates.

### AMB-09 Branch code / member ID formats
- **Default:** Branch `BR-{CITY}-{NN}` e.g. `BR-KHI-01` (CITY = 3-letter code from a City lookup seeded with KHI, LHE, ISB, RWP, PEW, QTA, MUX, FSD, HYD, SKT; NN per city, 2+ digits, never reused). Member `M-{YYYY}-{NNNNN}` e.g. `M-2026-00012` — global per calendar year (Asia/Karachi), not branch-embedded because members can move branches. Application ref `APP-{YYYY}-{NNNNN}`. Generated via a counter table locked with `SELECT … FOR UPDATE` inside the creating transaction (gap-free for committed rows, safe under concurrency).
- **Impact if wrong:** Format is a single function; cosmetic.

### AMB-10 Applicant → member
- **Default:** Fields per BR-040…052. Duplicates flagged not rejected (avoid enumeration). Re-application after decline allowed; HR sees prior history. Applicant chooses preferred branch (Active/Forming only); HR of that branch decides; HR can reassign to another branch before deciding (audited). Accept creates member with branch = application branch, status Active, team/role set in the accept dialog (role defaults to "Volunteer").

### AMB-11 Teams and roles
- **Default:** **Teams** = per-branch lookup table managed by HR Lead (e.g. "Food Drive", "Teaching"). **Volunteer roles** = global lookup managed by Super Admin (Volunteer, Team Lead, Coordinator, Treasurer). Member has one team (nullable) and one volunteer role.

### AMB-12 Branch lifecycle effects
| Status | Public directory | Application form | Collections | Reports drafted | Members |
|---|---|---|---|---|---|
| Forming | Shown "Coming soon" | Selectable | Blocked | No | Can be accepted |
| Active | Shown | Selectable | Allowed | Yes | Normal |
| Paused | Shown with "Paused" badge | Not selectable | Blocked | No new drafts; open ones can still be submitted/reviewed | Remain, read-only? No: HR can still edit |
| Closed | Hidden | Not selectable | Blocked | No | Read-only; history retained |

Transitions: Forming→Active, Active→Paused, Paused→Active, {Forming, Active, Paused}→Closed (guard: no unsent collections, no open reports). Closed is terminal.

### AMB-13 Urdu scope
- **Default:** UI strings fully translated; CMS content per language; operational data (names, notes) stored as entered (no translation); branch names have `name_en` + `name_ur`. **Font: Noto Naskh Arabic** (UI-friendly, compact line height, ~70–90 KB subset woff2) rather than Noto Nastaliq Urdu (more traditional but ~2× size and very tall line-height that breaks tables) — trade-off documented in an ADR; Nastaliq for headings only is OPT-07. Numerals: Western digits (0-9) in both locales for financial clarity; dates Gregorian with localised month names. PDFs: WeasyPrint (Pango/HarfBuzz) shapes Urdu correctly.
- **Impact if wrong:** Judges who read Urdu may prefer Nastaliq; switch is a font-file swap.

### AMB-14 CSV/PDF scope
- **Default:** CSV: collections, unsent collections, weekly reports list, members, audit log. PDF: single weekly report (official copy, with status watermark "DRAFT" unless locked), monthly head-office summary. Exports audited. Role permissions in `05-…`.

### AMB-15 Content manager scope
- **Default:** Types: `PAGE_SECTION` (Home hero, About story, Get Involved intro, Contact details), `PROGRAM`, `EVENT`. States Draft/Published/Archived. Live snapshot on publish (editing doesn't change live until re-publish). No scheduled publishing (OPT-05). Version history via audit log before/after.

### AMB-16 Audit
- **Default:** Append-only table; UPDATE/DELETE blocked by trigger; SHA-256 hash chain; retention indefinite (document 7-year policy suggestion); viewer = Super Admin; per-entity history = anyone who can view the entity. "Every change" guaranteed architecturally (all writes via services, Django admin disabled in production) and verified by `T-AUD-COVERAGE`.

### AMB-17 Money
- **Default:** PKR only; `NUMERIC(12,2)` / Python `Decimal`; display `Rs 12,345.50` (en) and `12,345.50 روپے` (ur); never floats.

### AMB-18 "No online payments"
- **Default:** No payment gateway, no card/bank account fields, no "Donate now" button that implies online payment. Get Involved page explains donations are collected offline at branches with official receipts.

### AMB-19 Growth
- **Default:** All operational tables carry `branch_id` FK; no per-branch config in code; branch codes generated; dashboards aggregate by query; indexes on `(branch_id, date)`; test creating 50 branches with data and asserting totals/compliance remain correct.

### AMB-20 Applicant age / CNIC
- **Default:** Collect **date of birth** with minimum age **16** (minors 16–17 require guardian consent checkbox). **Do not collect CNIC** (high-sensitivity national ID; not needed to volunteer; data minimisation). If organisers' sample data includes CNIC, store masked last 4 only.

### AMB-21 Password recovery
- **Default:** No SMTP on Render free tier → no self-service reset; Super Admin issues a temporary password (user forced to change). Email backend = console. OPT-03 adds email.

### AMB-22 Organisation identity
- **Default:** Use the brand material when received. Until then, fictional name **"Ujala Volunteer Network"** (configurable `ORG_NAME`), footer note "Demo organisation for ShipLens 1.0". Q-03.

### AMB-23 Pre-window confusion around "§1.8"
- The prompt references "§1.8 point table"; this is §1.6 ("How it is judged"). Treated as §1.6.

### AMB-24 "Easy · ~2 hours" label on the event card
- The card says "~2 hours" but the deliverable list is a multi-week build. Treated as a platform UI label; does not change scope.

---

## Batched questions for you (answer when you can; defaults already applied)

| # | Question | Recommended default |
|---|---|---|
| Q-01 | ~~Which deadline is real?~~ **Answered: 2 Nov 23:59 PKT.** | — |
| Q-02 | ~~Send the sample data and brand material.~~ **Answered: none published.** We author our own CSV sample data + brand; ask once on the Discussion tab for the record. | — |
| Q-03 | Is there an official organisation name/logo in the brand pack? | "Ujala Volunteer Network" placeholder |
| Q-04 | Which language do you know best — Python or JavaScript/TypeScript? (Stack choice rests on explainability.) | Python/Django |
| Q-05 | Can you spend ~USD 13 (Render Starter web $7 + Basic Postgres $6, one month) to avoid cold starts and the 30-day free-DB expiry during judging? | Yes for 2 Nov–30 Nov; otherwise free tier + keep-warm ping |
| Q-06 | How many hours/day can you commit until 2 Nov? | ~10 h/day (≈ 95 h total) |
| Q-07 | Do you want Urdu in Nastaliq style (traditional) or Naskh (compact, faster)? | Naskh |
| Q-08 | Super Admin approving reports/applications: allow (convenience) or forbid (segregation of duties)? | Forbid |
