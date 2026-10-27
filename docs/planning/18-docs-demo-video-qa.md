# 18 — Documentation, Demo Video and Judge Q&A

## 1. `docs/` folder layout (deliverable)
```text
docs/
  README.md                 index of docs
  adr/0001-…md … 0012-…md   ADRs (Context · Decision · Consequences · Alternatives), dated
  architecture.md           C4 diagrams, module map, request lifecycle, ER diagram (Mermaid)
  permissions.md            GENERATED permission table (from code) + scope rules
  api.md                    route reference: every URL, method, action, roles, params, responses (test-checked)
  openapi.yaml              JSON endpoints: /health, /app/dashboard/data.json, /internal/generate-drafts
  data-model.md             tables, constraints, triggers
  business-rules.md         BR catalogue (from planning/07)
  handover.md               runbook for the next team (below)
  testing.md                how to run tests, coverage, E2E, LHCI
  security.md               OWASP mapping, threat model, reporting a vulnerability
  i18n.md                   adding strings/languages
  credits.md                generated licences of dependencies + assets
  screenshots/              en/ur public, dashboard, report states, audit, PDFs
  planning/                 this plan
```

## 2. README structure
1. Title, one-line pitch, badges (CI, coverage, licence, Python, Django).
2. **Live demo** link + "first load may take up to a minute" (if free tier) + `/health` link.
3. **Test logins table** (one per role):
   | Role | Email | Password | Lands on |
   |---|---|---|---|
   | Super Admin | superadmin.demo@shiplens.test | *(value of DEMO_PASSWORD, written here)* | Dashboard |
   | Finance Reviewer | finance.demo@shiplens.test | 〃 | Dashboard |
   | Content Editor | content.demo@shiplens.test | 〃 | Content |
   | Branch Lead (Karachi) | branchlead.demo@shiplens.test | 〃 | My branch |
   | HR Lead (Karachi + Lahore) | hr.demo@shiplens.test | 〃 | Applications |
   *Demo data is fictional. Demo accounts cannot change passwords; Super Admin can reset demo data.*
4. **Judge quick path** (≤ 2 min): how to verify each gate (dashboard Oct 2026 values; report R10 lifecycle; permission tests in CI; live link + CI badge).
5. Features ↔ brief deliverables table (22 rows, with links).
6. Screenshots (EN + UR).
7. Architecture summary + link to docs.
8. Tech stack + why (link ADR-001).
9. Local setup (Docker): `cp .env.example .env` → `docker compose up` → `docker compose run web python manage.py seed_demo` → open `http://localhost:8000`.
10. Running tests, coverage, lint, E2E, Lighthouse.
11. Deployment (Render blueprint, env vars table).
12. Env var table: `SECRET_KEY`, `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DEMO_MODE`, `DEMO_PASSWORD`, `WEB_CONCURRENCY`, `LOG_LEVEL`, `DRAFTS_TOKEN` (opt).
13. Expected dashboard values (link to table).
14. Known limitations (no email, no online payments by design, free-tier cold start, owner-role trigger caveat, no file uploads).
15. AI usage summary + link to AI-USAGE.md.
16. Credits & licence (MIT), "Solo entry for ShipLens 1.0", submitted version SHA.

## 3. `AI-USAGE.md` template and discipline
```markdown
# AI Usage Declaration
I used AI tools as allowed by the ShipLens rules. I reviewed, tested and can explain every line in this repository.

## Tools
| Tool | Version/model | Used for |
|---|---|---|
| Claude Code (Anthropic) | Claude Opus | Planning docs (docs/planning), design review, test-case brainstorming, … |

## Rules I followed
- No AI output committed without reading it line by line and running tests.
- No secrets or personal data pasted into AI tools.
- Business rules, data model and permission decisions are mine (see ADRs); AI suggested alternatives.

## Log
| Date | Tool | Task | Files | What I changed / verified |
|---|---|---|---|---|
| 2026-10-24 | Claude Code | Project planning documents | docs/planning/* | Reviewed and edited assumptions; chose Django; confirmed deadline |
```
Append one row per AI-assisted task, the same day. Include Urdu translation assistance explicitly.

## 4. Handover guide outline (`docs/handover.md`)
Purpose & users · system overview · environments · how to run locally · how to deploy · how to add a branch/user/city · how to change business rules (settings) · how to add a role/permission (matrix + tests + doc regen) · how to add a report field (registry) · how to add a language · backups/restore · rotating secrets & demo password · monitoring (`/health`, Render logs, audit) · incident checklist · known limitations & roadmap · contacts.

## 5. Video plan (≤ 5:00, own voice; target 4:40)

Follows the handbook's suggested outline (§07), which judges will expect.

| Time | Scene | What to say / show | Gate/row |
|---|---|---|---|
| 0:00–0:30 | Problem, stack, link | Problem in one sentence; Django + PostgreSQL on Render with Docker and GitHub Actions; live URL and `/health` JSON with the deployed commit SHA | G4 |
| 0:30–2:30 | Core flows | Public: submit an application (show one field error, then the reference) → HR Lead accepts → member `M-2026-…` created. Branch Lead logs a collection (lock countdown visible). Weekly report R10: Branch Lead submits → Finance returns with comment → Branch Lead resubmits → Finance approves → Locked. Dashboard (period Oct 2026): approved total moves when R9 is approved; read K1 73,250.50 and the unsent list | G1, G2, HO features |
| 2:30–3:30 | Refusals + audit | Branch Lead opens a Lahore report URL → 404; Content Editor opens collections → 403; mention the matrix tests run every role × every route in CI. Audit viewer filtered to R10: six events in order with before/after, actor, IP | G3, roles/audit |
| 3:30–4:30 | Urdu, CMS, exports | Switch to Urdu: public form, a table page and the dashboard mirrored RTL. Content Editor edits a program, publishes it, shows it live. Export collections CSV and the report PDF (Urdu) | CMS/bilingual, exports |
| 4:30–5:00 | Engineering | GitHub: green CI on `main`, coverage %, Dockerfile (multi-stage, non-root, HEALTHCHECK), `/health`; one line on AI usage | Testing, Docker, docs |

**Pre-recording checklist:** Render warmed (hit `/health` + pages 2 min before) · `Reset demo data` as SA · R10 in DRAFT · browser zoom 110 %, clean profile, no bookmarks bar · logins in a password-free notes window (not on screen) · two windows (BL / FR) side by side · mic test · OBS 1080p · close notifications · rehearse twice with stopwatch.
**Fallback if Render is cold/down:** record with local Docker stack (same image, same seed), say so, and show the live `/health` separately; keep a 30-second backup clip of the live site recorded on 1 Nov.

## 6. Judge Q&A prep sheet

| Module | Likely question | Short answer |
|---|---|---|
| Architecture | Why Django and not Next.js? | Security defaults (CSRF, sessions, Argon2), mature i18n with RTL, WeasyPrint shapes Urdu in PDFs, server-rendered pages give Lighthouse 90+ with no JS, and I can trace every request end to end. |
| | How is the code layered? | URL → view (thin: permission + form) → service (rules, transaction, audit) → model (constraints). Read-only queries in selectors/KPIs. |
| | What happens if two people approve the same report? | Service locks the row (`SELECT … FOR UPDATE`) and checks state + revision; the second gets 409. |
| RBAC | Where are permissions defined? | One dict in `accounts/permissions.py`; docs table is generated from it; tests are parametrised from it. |
| | How do you stop a Branch Lead reading another branch by changing the id? | Every lookup uses `scope_queryset` filtered by assigned branches → 404. Tested per resource. |
| | What if a developer adds a route and forgets permissions? | Route registry middleware denies unregistered routes, and `T-RBAC-ROUTES` fails CI. |
| Audit | How do you guarantee every change is recorded? | All writes are in services, which call `audit.record` in the same transaction; a test hits every POST route and asserts an audit row; Django admin is off. |
| | Can someone edit the audit log? | DB triggers reject UPDATE/DELETE; a SHA-256 hash chain detects tampering; limitation: DB owner could drop triggers — production would use a separate role. |
| | What's stored? | Actor, role, time, action, entity, branch, changed fields before/after, IP, UA, request id, hash. |
| Collections | 7 days from what? | From `created_at` (server time), so it can't be gamed by backdating; computed on each request, so no cron; configurable. |
| | How do you fix a mistake after lock? | You don't edit history; an adjustment entry with a reason is recorded in the current week. |
| | What is "unsent"? | Not voided and not part of a transfer to the main account. Branch Lead records transfers with a bank reference. |
| Reports | How is it "drafted automatically"? | Lazily and idempotently when the branch opens Reports or the dashboard loads, plus a command; unique (branch, week) prevents duplicates; figures computed live until submit. |
| | Why can't later changes alter an approved report? | On submit we snapshot totals and line items; approval locks the row and lines with a DB trigger; dashboard approved totals read the snapshot lines. |
| | Why separate Approved and Locked? | The brief lists both steps; two audit events; easy to change if lock rules change. |
| Dashboard | How did you verify the numbers? | Hand-calculated table in docs; `T-DASH-SEED` asserts each value with Decimal equality at a fixed date. |
| | Timezones? | Stored UTC; business dates in Asia/Karachi through one clock module. |
| Security | How do you handle CSRF/XSS/SQLi? | Django CSRF tokens on every POST; autoescape + nh3 sanitising + strict CSP with no inline scripts; ORM parameterised queries only. |
| | Why sessions not JWT? | Server-rendered same-origin app; sessions are revocable and keep tokens away from JavaScript. |
| | Brute force? | django-axes lockout after 5 failures for 15 min; Argon2id hashing; generic error messages. |
| Testing | What's your coverage and what's not covered? | ≥ 70 % (exact number from CI); templates and some error branches less covered; critical services ≥ 85 %. |
| | How do you test time-based rules? | Injectable clock + time-machine; boundary tests at 7 days minus one second and exactly 7 days. |
| | How do you test concurrency? | TransactionTestCase with threads hitting ID generation and accept; assert unique sequential IDs. |
| DevOps | What does your Dockerfile do? | Multi-stage: build wheels in builder, slim runtime with Pango for PDFs, non-root user, compile translations + collectstatic, HEALTHCHECK on /health. |
| | How do migrations run on Render? | Start script runs `migrate` before gunicorn (pre-deploy is paid-only); deploys only after CI checks pass. |
| | What if the DB is down? | `/health` returns 503; Render health check marks deploy unhealthy; app shows generic error. |
| i18n | How does RTL work? | `dir="rtl"` from Django's bidi flag; CSS uses logical properties so one stylesheet works both ways; numbers wrapped in `<bdi>`. |
| | How do you know Urdu is complete? | Parity test: 100 % translated, no fuzzy, placeholders match. |
| CMS | What if an editor changes a published page? | Edits go to the working copy; the live site serves the published snapshot until "Publish changes". |
| Twist | How quickly could you add a new role? | Add enum value + matrix column; tests and docs regenerate; ~1–2 h. |
| AI | Which parts did AI help with, and how did you check them? | Listed in AI-USAGE.md by date and file. Codex wrote code in small steps from my planning prompts; I reviewed every step before committing, ran the tests, and sent fixes back (examples in the log: request-ID validation, proxy-aware IP, removing an unneeded migration backfill). Ask me about any file. |
| Scale | What would you change to support 500 branches? | The data model already scales: every table is keyed by branch with indexes on (branch, date) and (branch, status); codes come from per-city counters. I'd add: dashboard aggregates computed once per request into a small summary table or materialised view, pagination on every list (already there), a paid Render instance with more workers, Postgres connection pooling, and a background job for weekly drafts instead of lazy creation. The 50-branch growth test would move to 500. |
| Lock | Show me the test that proves the 7-day lock. | `tests/finance/…`: `test_collection_editable_on_day_7` and `test_collection_locked_on_day_8` freeze the clock; plus exact-boundary tests at 7 days minus one second and exactly 7 days, and one that changes the setting to 3 days. |
