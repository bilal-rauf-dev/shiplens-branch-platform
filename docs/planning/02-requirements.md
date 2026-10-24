# 02 — Requirements Catalogue

**Tags:** **E** = Explicit (stated in the brief) · **I** = Implicit (unavoidable consequence of the brief) · **A** = Assumed (my decision; listed in `21-assumptions-and-open-questions.md`).
Each REQ is atomic and testable. "Test" column references IDs in `17-test-strategy.md`; "Task" references WBS IDs in `19-work-plan-plan-a-and-b.md`.

## 0. Problem restatement (< 200 words)

A volunteer organisation runs programmes through city branches. Branch volunteers and cash collections live in scattered Excel files and WhatsApp threads; head office re-types weekly numbers into a master sheet with no validation, no approval and no history, so totals cannot be trusted and nobody can tell who changed what. The public has no authoritative place to learn about the organisation, find a branch or apply to volunteer.

The system replaces all of that with one web platform: a bilingual (English/Urdu, RTL) public website with a volunteer application form, and a secure back office where branches log members and offline collections, weekly reports are generated, submitted, reviewed and locked, and head office sees approved figures live.

"Production-grade, ready for real use from day one" means concretely: deployed on a public HTTPS URL with a managed database; real authentication with least-privilege roles enforced on the server; every change auditable and tamper-resistant; inputs validated and outputs encoded (OWASP); automated tests and CI gating every merge; reproducible Docker builds, migrations on deploy, health checks; no demo shortcuts that would be unsafe with real data; documentation that lets someone else run and maintain it.

## 1. Compliance & delivery (COMP)

| ID | Requirement | Tag | Test / Verification | Task |
|---|---|---|---|---|
| REQ-001 | Source is in a public GitHub repository licensed MIT. | E | C-01, C-02 | W-01 |
| REQ-002 | Repository has ≥ 25 commits on ≥ 7 distinct days, all dated ≥ task-open date. | E | C-10, C-14, C-15 | all |
| REQ-003 | ≥ 3 pull requests are merged into `main` from feature branches. | E | C-16 | all |
| REQ-004 | A live deployment on Render backed by Render PostgreSQL is reachable over HTTPS. | E | C-03, `E2E-LIVE` | W-05 |
| REQ-005 | README and AI-USAGE.md exist; AI-USAGE lists every AI tool and its use. | E | C-06, C-07 | W-90 |
| REQ-006 | One working test login exists per role (5) and is documented. | E | C-08, `T-SEED-USERS` | W-50 |
| REQ-007 | `docs/` contains ADRs, API docs, permission table and a handover guide. | E | D-19 | W-91 |
| REQ-008 | A ≤ 5-minute walkthrough video in my own voice is produced. | E | C-05 | W-95 |
| REQ-009 | The final judged commit hash is recorded and tagged `v1.0.0`. | E | C-04 | W-99 |
| REQ-010 | Only provided sample data or clearly fictional seed data is used; no real personal data in repo or live DB. | E | C-18 | W-50 |
| REQ-011 | All open-source libraries and assets are credited with licences. | E | C-12 | W-91 |

## 2. Public website (PUB)

| ID | Requirement | Tag | Test | Task |
|---|---|---|---|---|
| REQ-020 | Public pages exist: Home, About, Programs, Branches, Events, Get Involved, Contact. | E | `E2E-01`, `T-PUB-PAGES` | W-60 |
| REQ-021 | Every public page is available in English (`/en/…`) and Urdu (`/ur/…`). | E | `T-PUB-PAGES[ur]` | W-70 |
| REQ-022 | Programs, Events and page sections are rendered only from **published** CMS content. | I | `T-CMS-PUBLIC-ONLY-PUBLISHED` | W-61 |
| REQ-023 | Branches page lists branches with status Active, Paused (badge) and Forming ("coming soon"); Closed branches are hidden. | A | `T-PUB-BRANCH-VISIBILITY` | W-60 |
| REQ-024 | Get Involved page hosts the volunteer application form. | E | `E2E-02` | W-30 |
| REQ-025 | Contact page shows head-office contact details and links to the branch directory (no contact form in MVP). | A | `T-PUB-PAGES` | W-60 |
| REQ-026 | Public pages have unique `<title>`, meta description, `hreflang` alternates, sitemap.xml and robots.txt. | I | `T-PUB-SEO` | W-62 |
| REQ-027 | Public pages never expose internal data (member names, amounts, applicant data). | I | `T-PUB-NO-LEAK` | W-60 |

## 3. Volunteer application (APP)

| ID | Requirement | Tag | Test | Task |
|---|---|---|---|---|
| REQ-030 | Anonymous visitors can submit an application with the fields in `07-business-rules.md` BR-040…BR-052. | E | `T-APP-SUBMIT-OK` | W-30 |
| REQ-031 | Every field is validated server-side (type, required, length, format) with localised messages; client-side HTML5 attributes mirror the rules. | E | `T-APP-VALIDATION-*` | W-30 |
| REQ-032 | Form is protected against spam: honeypot, minimum fill time, per-IP rate limit, CSRF. | I | `T-APP-SPAM-*` | W-30 |
| REQ-033 | Submission returns a reference `APP-YYYY-NNNNN` without revealing whether the person already applied. | A | `T-APP-NO-ENUM` | W-30 |
| REQ-034 | Possible duplicates (same normalised email or phone with a pending application or non-left member) are flagged for HR, not rejected. | A | `T-APP-DUP-FLAG` | W-31 |
| REQ-035 | HR Lead sees pending applications only for branches they are assigned to. | E/A | `T-RBAC-SCOPE-APP` | W-31 |
| REQ-036 | HR Lead can accept or decline a pending application; decline requires a reason. | E/A | `T-APP-DECIDE-*` | W-31 |
| REQ-037 | Accepting creates exactly one member with an auto-generated unique ID, atomically, in the same transaction as the status change. | E | `T-APP-ACCEPT-ATOMIC`, `T-APP-ACCEPT-RACE` | W-31 |
| REQ-038 | Accepted/declined applications are immutable (terminal states). | I | `T-APP-TERMINAL` | W-31 |
| REQ-039 | Applicant must give explicit consent to the privacy notice; consent timestamp stored. | I | `T-APP-CONSENT` | W-30 |

## 4. Authentication & roles (AUTH / RBAC)

| ID | Requirement | Tag | Test | Task |
|---|---|---|---|---|
| REQ-040 | Staff log in with email + password; sessions are server-side cookies (HttpOnly, Secure, SameSite=Lax). | E/A | `T-AUTH-LOGIN`, `T-SEC-COOKIES` | W-10 |
| REQ-041 | Exactly five roles exist: Super Admin, Finance Reviewer, Content Editor, Branch Lead, HR Lead; each user has exactly one role. | E/A | `T-RBAC-ROLES` | W-11 |
| REQ-042 | Permissions are defined in one matrix (code) and published as `docs/permissions.md` generated from it. | E | `T-RBAC-DOC-SYNC` | W-11 |
| REQ-043 | Default deny: any route not declared in the permission registry returns 403/404 for authenticated users and redirects anonymous users to login. | I | `T-RBAC-ROUTES` | W-11 |
| REQ-044 | Branch Lead and HR Lead are restricted to data of branches they are assigned to (row-level scope). | E/A | `T-RBAC-SCOPE-*` | W-11 |
| REQ-045 | Only Super Admin creates/deactivates users, assigns roles and branch assignments. | A | `T-RBAC-MATRIX` | W-12 |
| REQ-046 | Failed logins are rate-limited / locked out (5 failures → 15 min lockout per account+IP). | I | `T-SEC-LOCKOUT` | W-10 |
| REQ-047 | Passwords hashed with Argon2id; min length 12; common passwords rejected. | I | `T-SEC-PASSWORD` | W-10 |
| REQ-048 | Users flagged `must_change_password` are forced to change it at next login. | A | `T-AUTH-FORCE-CHANGE` | W-12 |
| REQ-049 | Demo accounts exist only when `DEMO_MODE=true`; their passwords cannot be changed through the UI; Super Admin can "reset demo data". | A | `T-SEED-DEMO-ONLY` | W-50 |

## 5. Branch register (BRN)

| ID | Requirement | Tag | Test | Task |
|---|---|---|---|---|
| REQ-050 | Super Admin can create a branch; its code is generated automatically as `BR-{CITY}-{NN}` and is immutable. | E/A | `T-BRN-CODE-*` | W-20 |
| REQ-051 | Branch codes are unique and generated safely under concurrency. | I | `T-BRN-CODE-RACE` | W-20 |
| REQ-052 | Branch status lifecycle is Forming → Active ↔ Paused → Closed with only the transitions in `06-state-machines.md`. | E | `T-BRN-TRANSITIONS` | W-20 |
| REQ-053 | Closing a branch requires zero unsent collections and zero open (submitted/resubmitted/returned) reports. | A | `T-BRN-CLOSE-GUARD` | W-20 |
| REQ-054 | Collections can be logged only for Active branches. | A | `T-COL-BRANCH-ACTIVE` | W-40 |
| REQ-055 | Applications can target only Active or Forming branches. | A | `T-APP-BRANCH-OPEN` | W-30 |
| REQ-056 | Adding a branch requires no code or schema change (growth). | E (Goal) | `T-GROWTH-N-BRANCHES` | W-20 |

## 6. Members (MEM)

| ID | Requirement | Tag | Test | Task |
|---|---|---|---|---|
| REQ-060 | Member IDs are generated automatically as `M-YYYY-NNNNN` (global yearly sequence), unique and immutable. | E/A | `T-MEM-ID-*` | W-31 |
| REQ-061 | A member has branch, team (optional, same branch), volunteer role, status (Active/Inactive/Left), joined date. | E | `T-MEM-MODEL` | W-32 |
| REQ-062 | Member list supports search (name, member ID, email, phone) and filters (branch, team, role, status, joined range). | E | `T-MEM-SEARCH-*` | W-32 |
| REQ-063 | Member list is paginated (25/page) and sorted (default: newest). | I | `T-MEM-PAGINATION` | W-32 |
| REQ-064 | HR Lead manages teams of assigned branches; Super Admin manages the global volunteer-role list. | A | `T-RBAC-MATRIX` | W-32 |
| REQ-065 | Member status follows the member state machine; Left is terminal except Super Admin reinstate. | A | `T-MEM-STATUS` | W-32 |

## 7. Collections (COL)

| ID | Requirement | Tag | Test | Task |
|---|---|---|---|---|
| REQ-070 | Branch Lead logs offline collections: date, amount (PKR), method (Cash / Cheque / Bank deposit), receipt book number, optional collector member, note. | E | `T-COL-CREATE` | W-40 |
| REQ-071 | No online payment capability exists (no card fields, no gateway, no payment links). | E | `T-COL-NO-ONLINE` (static check), review | W-40 |
| REQ-072 | A collection becomes **locked** 7 days (configurable) after it was recorded (`created_at`), after which it cannot be edited or voided by anyone. | E/A | `T-COL-LOCK-*` | W-40 |
| REQ-073 | Collections are never hard-deleted; an open collection can be voided with a reason; voided entries are excluded from totals. | A | `T-COL-VOID` | W-40 |
| REQ-074 | A collection dated in a week whose report is Submitted/Resubmitted/Approved/Locked cannot be created or edited. | A | `T-COL-WEEK-CLOSED` | W-40 |
| REQ-075 | Collection date cannot be in the future nor more than lock-days in the past. | A | `T-COL-DATE-RANGE` | W-40 |
| REQ-076 | Branch Lead records a transfer to the main account (date, bank reference) covering one or more unsent collections; those become **Sent** and immutable. | E/A | `T-XFER-*` | W-41 |
| REQ-077 | Amounts stored as exact decimals (NUMERIC(12,2)), > 0. | I | `T-COL-AMOUNT` | W-40 |

## 8. Weekly reports (RPT)

| ID | Requirement | Tag | Test | Task |
|---|---|---|---|---|
| REQ-080 | A weekly report exists per (branch, ISO week Mon–Sun, Asia/Karachi); it is drafted automatically (lazily on first access and by an idempotent command). | E/A | `T-RPT-AUTODRAFT` | W-42 |
| REQ-081 | Draft figures are computed live from collections, members and applications of that branch-week. | E/I | `T-RPT-AGGREGATES` | W-42 |
| REQ-082 | Branch Lead can edit narrative fields and submit a Draft; submission snapshots totals and line items. | E | `T-RPT-SUBMIT` | W-42 |
| REQ-083 | Finance Reviewer can approve or return a submitted/resubmitted report; return requires a comment. | E | `T-RPT-RETURN` | W-42 |
| REQ-084 | Branch Lead can correct and resubmit a returned report; revision number increments; a new snapshot is taken. | E | `T-RPT-RESUBMIT` | W-42 |
| REQ-085 | Approval locks the report immediately; a locked report and its line items cannot be modified (service + DB trigger). | E | `T-RPT-LOCKED-IMMUTABLE` | W-42 |
| REQ-086 | Every transition (draft created, submitted, returned, resubmitted, approved, locked) writes an audit event. | E (Gate 2) | `T-RPT-LIFECYCLE` | W-42 |
| REQ-087 | Finance Reviewer cannot edit report figures. | A | `T-RBAC-MATRIX` | W-42 |
| REQ-088 | Report fields are defined in one registry so a new field can be added without schema migration. | A (twist) | `T-RPT-FIELD-REGISTRY` | W-42 |

## 9. Dashboard (DASH)

| ID | Requirement | Tag | Test | Task |
|---|---|---|---|---|
| REQ-090 | Head-office dashboard (Super Admin, Finance Reviewer) shows the KPIs K1–K10 defined in `09-…`. | E | `T-DASH-SEED` | W-51 |
| REQ-091 | Dashboard shows 12-month trends of collected vs approved amounts and new members, zero-filled. | E | `T-DASH-TRENDS` | W-51 |
| REQ-092 | Dashboard lists all unsent (unrouted) collections with branch, date, amount, age, lock state. | E | `T-DASH-UNSENT` | W-51 |
| REQ-093 | With the seed (or provided sample) data loaded, every dashboard value equals the hand-calculated expected value. | E (Gate 1) | `T-DASH-SEED` | W-50 |
| REQ-094 | Dashboard reflects new approvals immediately (no caching beyond the request). | E ("real time") | `T-DASH-REALTIME` | W-51 |
| REQ-095 | Branch Lead sees a branch-scoped dashboard for their branch. | A | `T-RBAC-SCOPE-DASH` | W-51 |

## 10. Exports (EXP)

| ID | Requirement | Tag | Test | Task |
|---|---|---|---|---|
| REQ-100 | CSV export (UTF-8 with BOM) for: collections, weekly reports, members, unsent collections, audit log. | E/A | `T-EXP-CSV-*` | W-55 |
| REQ-101 | PDF export for a weekly report and for the monthly head-office summary, with correct Urdu shaping in Urdu mode. | E/A | `T-EXP-PDF-*` | W-56 |
| REQ-102 | Exports respect the same role scopes as screens. | I | `T-RBAC-SCOPE-EXP` | W-55 |
| REQ-103 | CSV cells beginning with `= + - @ \t \r` are neutralised (formula injection). | I | `T-EXP-CSV-INJECTION` | W-55 |
| REQ-104 | Every export writes an audit event (who, what, filters, row count). | A | `T-AUD-EXPORT` | W-55 |

## 11. Content manager (CMS)

| ID | Requirement | Tag | Test | Task |
|---|---|---|---|---|
| REQ-110 | Content Editor can create/edit Programs, Events and Page sections in English and Urdu. | E | `T-CMS-CRUD` | W-61 |
| REQ-111 | Content items have states Draft, Published, Archived; only Published items appear publicly. | E | `T-CMS-STATES` | W-61 |
| REQ-112 | Editing a published item does not change the live version until it is re-published ("unpublished changes"). | A | `T-CMS-LIVE-SNAPSHOT` | W-61 |
| REQ-113 | Rich text is sanitised on save and on render (no script injection). | I | `T-SEC-XSS-CMS` | W-61 |
| REQ-114 | Publishing requires both EN and UR title present (UR may fall back to EN body with a flag). | A | `T-CMS-PUBLISH-GUARD` | W-61 |

## 12. Audit (AUD)

| ID | Requirement | Tag | Test | Task |
|---|---|---|---|---|
| REQ-120 | Every create/update/transition/void/delete of a domain record writes an audit row in the same DB transaction. | E | `T-AUD-COVERAGE`, `T-AUD-ATOMIC` | W-13 |
| REQ-121 | Audit rows capture actor, role, time (UTC), action, entity type/id/label, branch, before, after, IP, user agent, request id. | E/I | `T-AUD-FIELDS` | W-13 |
| REQ-122 | Audit rows cannot be updated or deleted (DB trigger); a hash chain allows tamper detection. | I | `T-AUD-IMMUTABLE`, `T-AUD-CHAIN` | W-13 |
| REQ-123 | Security events are audited: login success/failure, logout, lockout, permission denied, password change. | I | `T-AUD-SECURITY` | W-13 |
| REQ-124 | Super Admin can browse and filter the audit log (actor, action, entity, branch, date) and export it. | E/A | `T-AUD-VIEWER` | W-14 |
| REQ-125 | Each record detail page shows its own history to users who can view the record. | A | `T-AUD-ENTITY-HISTORY` | W-14 |

## 13. Internationalisation (I18N)

| ID | Requirement | Tag | Test | Task |
|---|---|---|---|---|
| REQ-130 | All UI strings are translatable; Urdu translation complete (no missing/fuzzy entries). | E | `T-I18N-PARITY` | W-70 |
| REQ-131 | Urdu pages render with `lang="ur" dir="rtl"`; layout mirrored via CSS logical properties. | E | `T-I18N-DIR`, `E2E-03` | W-70 |
| REQ-132 | Language switcher on every page preserves the current path; choice persists (URL prefix + cookie). | I | `T-I18N-SWITCH` | W-70 |
| REQ-133 | CMS content is stored per language. | A | `T-CMS-CRUD` | W-61 |
| REQ-134 | Urdu PDFs are shaped correctly (joined letters, RTL). | I | `T-EXP-PDF-UR` (text extraction + visual check) | W-56 |

## 14. Security (SEC) — OWASP mapping in `11-security.md`

| ID | Requirement | Tag | Test | Task |
|---|---|---|---|---|
| REQ-140 | CSRF protection on all state-changing requests. | I | `T-SEC-CSRF` | W-10 |
| REQ-141 | Security headers: CSP (no inline script), HSTS, X-Content-Type-Options, Referrer-Policy, frame-ancestors none. | I | `T-SEC-HEADERS` | W-80 |
| REQ-142 | IDOR prevention: object lookups go through role-scoped querysets; out-of-scope ids return 404. | I | `T-RBAC-SCOPE-*` | W-11 |
| REQ-143 | Mass assignment prevented: forms whitelist fields; status/branch/codes never bound from input. | I | `T-SEC-MASS-ASSIGN` | W-80 |
| REQ-144 | Secrets only from environment; none committed; `DEBUG=False` in production; `check --deploy` passes. | I | CI step | W-03 |
| REQ-145 | Dependency vulnerability scan in CI (pip-audit) and Dependabot enabled. | I | CI step | W-03 |
| REQ-146 | Errors show generic pages (no stack traces); 404/403/500 templates localised. | I | `T-SEC-ERRORS` | W-80 |
| REQ-147 | Applicant/member PII visible only to HR Lead (scoped) and Super Admin. | A | `T-RBAC-MATRIX` | W-31 |

## 15. Quality, DevOps, performance (OPS / TEST / PERF)

| ID | Requirement | Tag | Test | Task |
|---|---|---|---|---|
| REQ-150 | Automated test suite with ≥ 60 % backend line coverage, enforced in CI. | E | CI `--cov-fail-under` | all |
| REQ-151 | GitHub Actions runs lint, migrations check, tests (Postgres service), coverage gate, dependency audit, Docker build + health smoke on every PR and on `main`. | E | CI run | W-03 |
| REQ-152 | CI is green on `main` at the final commit. | E (Gate 4) | CI badge | W-99 |
| REQ-153 | Multi-stage, non-root Dockerfile with HEALTHCHECK. | E/I | `docker inspect`, CI | W-04 |
| REQ-154 | `GET /health` returns 200 JSON `{status, db, version}` when DB reachable, 503 otherwise; no auth, no secrets. | E | `T-OPS-HEALTH` | W-04 |
| REQ-155 | Migrations run automatically on deploy; demo seed is a separate idempotent command. | I | deploy log | W-05 |
| REQ-156 | Lighthouse ≥ 90 for Performance, Accessibility, Best Practices, SEO on measured public pages (mobile). | E | LHCI job | W-81 |
| REQ-157 | Public pages meet WCAG 2.1 AA (contrast, labels, keyboard, focus). | I | axe in E2E, LHCI a11y | W-81 |
| REQ-158 | Time-dependent rules use an injectable clock and Asia/Karachi local dates. | I | `T-COL-LOCK-*` | W-02 |

## 16. Twist-readiness (TWIST)

| ID | Requirement | Tag | Test | Task |
|---|---|---|---|---|
| REQ-160 | Business constants (lock days, week start, code formats, min age, rate limits) live in one settings module / `system_settings` table, not scattered literals. | A | `T-CONFIG-LOCKDAYS` (change value → behaviour changes) | W-02 |
| REQ-161 | State machines are declared as transition tables so a state/transition can be added in one place. | A | `T-SM-TABLES` | W-20/W-42 |

## 17. Traceability: §1.6 scoring rows → REQs

| Scoring row (pts) | REQs |
|---|---|
| Architecture and code quality (15) | REQ-042, 043, 088, 151, 158, 160, 161 + ADRs (REQ-007) |
| Head office features end to end (15) | REQ-050–056, 070–077, 080–088, 090–095, 100–104 |
| Roles, permissions, audit trail (10) | REQ-040–049, 120–125, 147 |
| Security OWASP Top 10 (15) | REQ-032, 040, 046, 047, 103, 113, 140–147 |
| Automated testing + passing CI (15) | REQ-150, 151, 152 |
| Docker and deployment (10) | REQ-004, 153, 154, 155 |
| Content manager, bilingual, performance (10) | REQ-021, 110–114, 130–134, 156, 157 |
| Surprise twist (5) | REQ-160, 161, 088 |
| Documentation and demo (5) | REQ-005, 007, 008 |

## 18. Traceability: §1.7 gates → REQs

| Gate | REQs |
|---|---|
| G1 | REQ-090, 091, 092, 093 |
| G2 | REQ-080–086 |
| G3 | REQ-041–045, 142, 147 |
| G4 | REQ-004, 151, 152 |

## 19. Measurable success criteria

| # | Criterion | Target | Measured by | Maps to |
|---|---|---|---|---|
| SC-01 | Dashboard values equal expected table for reference period Oct 2026 (seed) | 100 % of K1–K10 match | `T-DASH-SEED` in CI; manual check on live | G1, HO features |
| SC-02 | Report lifecycle with 6 ordered audit events | Pass | `T-RPT-LIFECYCLE`; audit viewer on live | G2 |
| SC-03 | Permission matrix tests | Every (role × action) cell incl. anonymous asserted; 0 unregistered routes | `T-RBAC-MATRIX`, `T-RBAC-ROUTES`, `T-RBAC-SCOPE-*` | G3, Roles row |
| SC-04 | CI green on `main` at final SHA | All jobs pass | GitHub Actions | G4, Testing row |
| SC-05 | Live link | `/health` 200 with DB ok; all 7 public pages 200 in en+ur; 5 logins succeed | `E2E-LIVE` script run manually on 2 Nov | G4, Docker row |
| SC-06 | Backend coverage | ≥ 60 % enforced; target ≥ 75 % overall, ≥ 85 % on `services`/`policies` modules | pytest-cov | Testing row |
| SC-07 | Lighthouse (mobile, LHCI on CI build) on `/en/`, `/ur/`, `/en/get-involved/`, `/en/branches/`, `/en/events/` | ≥ 90 in **all four** categories (Performance, Accessibility, Best Practices, SEO); also spot-check live warm | LHCI job + manual PageSpeed on live | CMS/bilingual/perf row |
| SC-08 | OWASP coverage | Every category in `11-security.md` has a control and ≥ 1 automated test or CI check | traceability table | Security row |
| SC-09 | `manage.py check --deploy` | 0 warnings in production settings | CI step | Security, Docker |
| SC-10 | Urdu completeness | 0 untranslated/fuzzy msgids | `T-I18N-PARITY` | Bilingual |
| SC-11 | Docker | Image builds, runs as non-root, HEALTHCHECK healthy within 30 s, image < 400 MB | CI docker job | Docker row |
| SC-12 | Commit history | ≥ 40 commits, 10 distinct days, ≥ 8 merged PRs | `git`/`gh` commands | Gate check |
| SC-13 | Docs | ADRs ≥ 8, API doc complete for every route (test-checked), handover guide lets a fresh machine run app in ≤ 15 min | `T-DOC-ROUTES`, dry-run | Docs row |
| SC-14 | Video | ≤ 5:00, covers G1–G4 | stopwatch | Docs/demo row |
| SC-15 | Twist | Delivered within ≤ 3 h of reveal with tests | PR | Twist row |
