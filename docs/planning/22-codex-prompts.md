# 22 — Codex Prompts (development only)

## How to use
1. `AGENTS.md` at the repo root holds the permanent rules (stack, no git, layering, tests, step summaries). Codex reads it automatically, so the prompts below don't repeat it.
2. For each PR: create the branch yourself → paste the prompt → Codex does **Step 1** and stops → review the diff (use the review prompt in §R if anything is unclear) → run the checks → commit with the given message → reply `continue with step 2` → … → push and open the PR with the given title/body → wait for CI → merge with **merge commit**.
3. Never let Codex commit, push or open PRs. If it tries, stop it.
4. After each PR, append a row to `AI-USAGE.md` (tool: Codex; task; files; what you changed/verified).

## Revised calendar (work starts Sun 25 Oct; plan shifted one day)

| Day | Prompts | PRs |
|---|---|---|
| Sun 25 Oct | (manual) repo init + planning docs, **P1** walking skeleton | #1, #2 |
| Mon 26 Oct | **P2** auth, RBAC, audit | #3 |
| Tue 27 Oct | **P3** branches, **P4** applications | #4, #5 |
| Wed 28 Oct | **P5** members, **P6** collections | #6, #7 |
| Thu 29 Oct | **P7** weekly reports | #8 |
| Fri 30 Oct | **P8** sample data + dashboard, **P9** exports | #9, #10 |
| Sat 31 Oct | **P10** CMS + public site, **P11** Urdu/RTL | #11, #12 |
| Sun 1 Nov | **P12** E2E + Lighthouse, **P13** hardening, **P14** docs (feature freeze 12:00) | #13, #14, #15 |
| Mon 2 Nov | **P15** twist (whenever revealed), **P16** release, video, submit by 18:00 | #16, #17 |

That's 9 distinct commit days (≥ 7 ✓) and about 55 commits. The buffer is now Mon 2 Nov morning only, so apply the cut-line in `19-…` §5 early if any day overruns by more than 3 hours.

---

## P0 — Manual (you, today, no Codex)

Branch `main` (before protection):
- Add `LICENSE` (MIT, "Copyright (c) 2026 <your name>"), `README.md` (title + one line), `AI-USAGE.md` (template from `18-…` §3 with the planning row), `.gitignore` (Python + `.env` + `staticfiles/` + `.coverage` + `htmlcov/` + `node_modules/`), `AGENTS.md`.
- Commit: `chore: initialise repository with MIT licence, README stub and AI-USAGE log`

Branch `docs/planning`:
- Commit 1: `docs(planning): add project plan, requirements and compliance matrix` (files 00–04, 21)
- Commit 2: `docs(planning): add data model, RBAC matrix, state machines and Codex prompts` (rest)
- **PR #1 title:** `docs: project plan and architecture decisions`
- **PR #1 body:**
  ```markdown
  ## Summary
  Planning set for ShipLens 1.0 under `docs/planning/`: requirements, compliance matrix, RBAC permission table, state machines, business rules, data model, dashboard expected values, architecture, security, test strategy and delivery plan. Adds `AGENTS.md` rules for AI coding agents.

  ## Why
  Design decisions are fixed before coding so the implementation stays traceable (REQ → BR → test).

  ## Notes
  Planning was AI-assisted and is declared in AI-USAGE.md. I reviewed every decision.
  ```

---

## P1 — Walking skeleton → PR #2

**Branch:** `chore/project-skeleton`
**PR title:** `chore: walking skeleton — Django, Docker, CI, Render, /health`

```text
TASK P1 — Walking skeleton. Work in 5 steps; stop after each step and print the step summary from AGENTS.md.

Read first: AGENTS.md, docs/planning/10-architecture-and-stack.md (§2, §5), docs/planning/15-devops-ci-cd-git.md (§1–§5), docs/planning/12-i18n-rtl.md (§3).

STEP 1 — Django project scaffold
- requirements.in (+ requirements-dev.in) with the stack from AGENTS.md; compile to requirements.txt / requirements-dev.txt with pip-tools and hashes.
- Django project in `config/` with split settings: config/settings/base.py, prod.py, test.py, dev.py. All secrets/hosts from env (SECRET_KEY, DATABASE_URL via dj-database-url, DJANGO_ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, DEMO_MODE, DEMO_PASSWORD, LOG_LEVEL). TIME_ZONE="Asia/Karachi", USE_TZ=True, LANGUAGES en/ur, LOCALE_PATHS, i18n_patterns with prefix_default_language=True.
- apps/core with: clock.py (now(), today() in Asia/Karachi), rules.py (get(name) returning defaults from settings.BUSINESS_RULES; system_settings override comes later in P2), middleware.py (RequestIdMiddleware: read/generate X-Request-ID, store in a contextvar, echo in the response header).
- templates/base.html (html lang/dir from LANGUAGE_CODE/LANGUAGE_BIDI, skip link, header/nav placeholder, main, footer) and a placeholder public home view at /<lang>/ saying "ShipLens" (wrapped for translation).
- static/css/main.css: CSS custom properties from docs/planning/16-ux-design-screens.md §2, a minimal reset and layout using logical properties only.
- pyproject.toml: ruff config (select E,F,I,B,S,DJ,UP; banned-api: django.utils.timezone.now and datetime.date.today outside apps/core/clock.py), pytest config (DJANGO_SETTINGS_MODULE=config.settings.test, --cov=apps).
- tests: test_t_clock_pkt (UTC 2026-10-25 20:30 → PKT date 2026-10-26), home page returns 200 for /en/ and /ur/ with correct dir attribute.
Acceptance: `python manage.py check` clean; ruff clean; pytest green against local Postgres.
Commit message: chore: scaffold Django 5.2 project with split settings

STEP 2 — /health endpoint
- GET /health (outside i18n_patterns): JSON {status, db, version, time}; DB check `SELECT 1` with a short timeout; 200 when OK; 503 with {"status":"degraded","db":"error"} on any DB exception (no exception text leaked). version = env RENDER_GIT_COMMIT or GIT_SHA (short, 7 chars) or "dev". Header Cache-Control: no-store.
- Tests: test_t_ops_health (200, keys present), test_t_ops_health_dbdown (patch the cursor to raise → 503, body has no traceback).
Commit message: feat(core): add /health endpoint with database check

STEP 3 — Docker
- Multi-stage Dockerfile exactly per 15-devops §1 (builder + slim runtime, Pango/HarfBuzz libs, non-root uid 10001, compilemessages + collectstatic at build with a dummy SECRET_KEY, Python-based HEALTHCHECK, ENTRYPOINT bin/start.sh).
- bin/start.sh: set -e; python manage.py migrate --noinput; if DEMO_MODE=true and the seed command exists, run `seed_demo --if-empty` (guard with `manage.py help seed_demo` so it's skipped until P8); exec gunicorn config.wsgi --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --timeout 60 --max-requests 500 --access-logfile -.
- .dockerignore, compose.yaml (db postgres:16-alpine with pg_isready healthcheck + named volume; web builds the image, dev command override runserver, env_file .env, depends_on db healthy), .env.example with every variable documented.
- WhiteNoise configured (CompressedManifestStaticFilesStorage) in base settings.
Acceptance: `docker compose up --build` → http://localhost:8000/health returns ok; `docker run --rm <image> id -u` prints 10001.
Commit message: chore(docker): add multi-stage non-root Dockerfile and compose

STEP 4 — GitHub Actions CI
- .github/workflows/ci.yml with jobs lint, test, security, docker exactly per 15-devops §4.1 (no e2e/lighthouse yet). test job: postgres:16 service with health-cmd; run `manage.py check --deploy --fail-level WARNING --settings=config.settings.prod` with dummy env; `makemigrations --check --dry-run`; `pytest --cov=apps --cov-report=xml --cov-report=term-missing --cov-fail-under=60`; write the coverage total to $GITHUB_STEP_SUMMARY. security: pip-audit + gitleaks. docker: build with GIT_SHA, run with a postgres container via a compose.ci.yml, wait for health, curl /health, assert non-root.
- Pin all third-party actions to full commit SHAs (with a version comment). Workflow-level `permissions: contents: read`. Cancel superseded runs with `concurrency`.
- .github/dependabot.yml (pip, github-actions, docker; weekly), .github/workflows/codeql.yml (python), .github/pull_request_template.md per 15-devops §6.1.
- prod.py must pass check --deploy: SECURE_SSL_REDIRECT, SECURE_PROXY_SSL_HEADER, HSTS 31536000 + include subdomains, secure cookies, SESSION_COOKIE_NAME="__Host-sid", CSRF_COOKIE_NAME="__Host-csrftoken", X_FRAME_OPTIONS=DENY, SECURE_REFERRER_POLICY="same-origin".
Acceptance: YAML valid (actionlint if available); describe how each job maps to the plan.
Commit message: ci: add lint, test, security and docker jobs

STEP 5 — Render blueprint
- render.yaml per 15-devops §5.1 (web: runtime docker, region singapore, plan free, healthCheckPath /health, autoDeployTrigger checksPass, env vars incl. SECRET_KEY generateValue, DATABASE_URL fromDatabase, DEMO_PASSWORD sync:false; database: postgres 16 free, singapore).
- README: add a "Run locally" section (docker compose up) and a "Deploy" section (Render Blueprint steps, env vars table).
Commit message: chore(render): add render.yaml blueprint

OUT OF SCOPE: users/auth, any domain models, seed data, e2e, Lighthouse.
```

**PR #2 body:**
```markdown
## Summary
Walking skeleton: Django 5.2 project with split settings, `/health` (DB check, version), multi-stage non-root Dockerfile, compose for local dev, GitHub Actions CI (lint, tests with Postgres + 60% coverage gate, pip-audit, gitleaks, Docker smoke test), CodeQL, Dependabot, Render blueprint.

## Why
Deploy first so every later feature ships to the live link and is gated by CI (Gate 4, Docker & deployment row).

## Tests
- `/health` OK and DB-down (503)
- PKT clock boundary
- `/en/` and `/ur/` render with the correct `dir`

## Traceability
REQ-004, REQ-151, REQ-153, REQ-154, REQ-155, REQ-158

## Checklist
- [x] CI green
- [x] `check --deploy` clean
- [x] AI-USAGE.md updated
```
**After merge (you):** create the Render Blueprint from the repo, set `DEMO_PASSWORD`, confirm the live `/health`. In GitHub settings, enable branch protection on `main` (require PR + checks lint/test/security/docker, no force-push), allow **merge commits only**.

---

## P2 — Auth, RBAC, audit → PR #3

**Branch:** `feat/auth-rbac-audit`
**PR title:** `feat: authentication, RBAC matrix and audit foundation`

```text
TASK P2 — Authentication, permission matrix, route registry and audit log. 6 steps; stop after each.

Read first: AGENTS.md, docs/planning/05-rbac-matrix.md (all), 08-data-model.md (§3.1, §3.4, §3.16, §3.17, §4), 11-security.md (§1, §2, §4), 07-business-rules.md (BR-130…BR-133), 17-test-strategy.md (§3.1).

STEP 1 — Custom user + login
- apps/accounts: User(AbstractBaseUser) with a custom UserManager (no PermissionsMixin, no is_staff/is_superuser: authorisation uses our own matrix) with email login, full_name, role (TextChoices: SUPER_ADMIN, FINANCE_REVIEWER, CONTENT_EDITOR, BRANCH_LEAD, HR_LEAD) with a CheckConstraint, is_active, is_demo, must_change_password, preferred_language; case-insensitive unique email (UniqueConstraint on Lower("email")). AUTH_USER_MODEL set before the first migration.
- Argon2 first in PASSWORD_HASHERS; validators: MinimumLength 12, CommonPassword, UserAttributeSimilarity, Numeric.
- django-axes: 5 failures, 15 min cooloff, lockout keyed on username+IP; reads the client IP via core.net.client_ip() (proxy-appended X-Forwarded-For entry, counted from the right).
- Login/logout views (logout POST-only), change-password view; middleware redirecting users with must_change_password to change-password; generic error "Email or password is incorrect."; role home redirect after login (05 §1.2 / 16 §1.2: SA/FR → dashboard placeholder, BL → branch placeholder, HR → applications placeholder, CE → content placeholder).
- Session settings: DB sessions, 8 h max, SESSION_SAVE_EVERY_REQUEST with 1 h idle via a small middleware.
- Tests: T-AUTH-LOGIN, T-AUTH-FORCE-CHANGE, T-SEC-LOCKOUT (6th attempt blocked), T-SEC-PASSWORD (short and common rejected), T-SEC-PASSWORD-HASH (stored hash starts with "argon2"), T-SEC-SESSION-ROTATE (session key changes on login).
Commit: feat(accounts): add custom email user model with five roles and secure login

STEP 2 — Branch assignments + permission matrix
- Model UserBranchAssignment(user, branch, created_by, created_at), unique (user, branch). Branch doesn't exist yet: create a minimal apps/branches/models.py Branch with only id, code, name_en, status now (P3 extends it via a migration), OR declare the assignment in P3 — choose the minimal Branch now and say so.
- apps/accounts/permissions.py: PERMISSIONS dict exactly as 05-rbac-matrix §3 (action code → {role: GLOBAL | ASSIGNED}); ANON allowed actions in PUBLIC_ACTIONS. Functions: can(user, action, obj=None), require(user, action, obj=None) raising PermissionDenied, assigned_branch_ids(user), scope_queryset(user, action, qs, branch_field="branch_id").
- Copy the matrix into tests/rbac_expected.yaml (human-readable) and add test_rbac_matrix_matches_expected.
- Management command export_permissions → writes docs/permissions.md (markdown tables grouped as in 05 §3 + the scope rules); test T-RBAC-DOC-SYNC compares output to the committed file.
Commit: feat(accounts): add central permission matrix and scoped querysets

STEP 3 — Route registry + view mixin
- apps/core/routes.py: ROUTE_ACTIONS {url_name: action} and PUBLIC_ROUTES set. RouteRegistryMiddleware: after URL resolution, unregistered url_names → 404; anonymous on non-public → redirect to login; authenticated without permission → 403 and audit "permission.denied" (throttled: one per user+route per minute via cache).
- PermissionRequiredMixin(required_action) for CBVs; also uses scope_queryset in get_queryset.
- Localised 403/404/500 templates; handler views.
- Tests: T-RBAC-ROUTES (walk the resolver; every named pattern registered), test that an unregistered dummy route 404s.
Commit: feat(core): add route registry middleware enforcing default deny

STEP 4 — Audit log
- apps/audit: AuditLog model per 08 §3.16; migration with RunSQL triggers rejecting UPDATE, DELETE and TRUNCATE (with reverse SQL).
- audit.record(actor, action, entity=None, *, entity_type=None, entity_id=None, entity_label="", branch_id=None, before=None, after=None, metadata=None): asserts connection.in_atomic_block; reads IP/UA/request id from the request contextvar; actor None → "system" or "anonymous" depending on context; redacts keys matching password/token/secret; diff helper storing only changed fields; hash chain under pg_advisory_xact_lock(<constant>) with sha256(prev_hash + canonical JSON (sorted keys, Decimal and datetime serialised as strings)).
- verify_chain() returning (ok, first_bad_id); management command verify_audit_chain.
- Signals for auth.login_succeeded, auth.login_failed (no password, email only), auth.logout, auth.locked_out (axes signal), auth.password_changed.
- Middleware sets the request context (ip from core.net.client_ip(), user agent truncated to 200, request id).
- Tests: T-AUD-IMMUTABLE (raw UPDATE/DELETE raise), T-AUD-ATOMIC (record + exception → nothing saved), T-AUD-CHAIN (verify ok; disable trigger inside the test, tamper with a row, verify fails at that id), T-AUD-REDACT, T-AUD-SECURITY (login ok/fail rows).
Commit: feat(audit): add append-only audit log with hash chain

STEP 5 — System settings + user admin (Super Admin)
- core.SystemSetting(key PK, value JSON, updated_by, updated_at); rules.get() now checks it first, then settings.BUSINESS_RULES. Settings page for SA (lock days 1–30, allow_submit_current_week, min_volunteer_age 14–25, apply_rate_per_hour 1–50), audited "settings.updated".
- Users list/create/edit/deactivate/reset-temp-password (SA only). Creating shows the temp password once and sets must_change_password. Assign branches. Can't deactivate or demote the last active SA. Demo accounts (is_demo) can't have their password reset and can't change their own password. All writes go through apps/accounts/services.py with audit events from 11 §4.1.
- Templates: simple tables and forms using the base layout.
Commit: feat(accounts): add user administration and system settings for super admin

STEP 6 — Matrix-driven permission tests
- tests/rbac/: a registry mapping each url_name → (method, URL builder, fixture factory for an in-scope object, expected success status). Parametrise over every role + ANON × every registered route; expected outcome derived from PERMISSIONS (allowed → success status; ANON → 302 to login; others → 403). Routes that don't exist yet are added by later PRs; the test must automatically include every route in ROUTE_ACTIONS and fail if a route has no registry entry.
- T-RBAC-SERVICE: calling a service with the wrong role raises PermissionDenied.
- T-AUD-DENIED: a denied request writes permission.denied.
Commit: test(rbac): add matrix-driven permission tests

OUT OF SCOPE: branch lifecycle, cities, applications, any finance features.
```

**PR #3 body:**
```markdown
## Summary
Email-based login with five roles, Argon2id hashing, django-axes lockout, forced password change; a central permission matrix with scoped querysets; a default-deny route registry; an append-only, hash-chained audit log; Super Admin user administration and system settings.

## Why
Gate 3 and the "roles, permissions and audit trail" row. Everything later builds on `can()`, `scope_queryset()` and `audit.record()`.

## Tests
- Matrix-driven permission tests across all roles + anonymous
- Route registry completeness
- Audit immutability, atomicity, hash-chain tamper detection, redaction
- Lockout, password policy, session rotation

## Traceability
REQ-040–049, REQ-120–124, BR-130–133

## Checklist
- [x] CI green
- [x] docs/permissions.md generated from code
- [x] AI-USAGE.md updated
```

---

## P3 — Branch register → PR #4

**Branch:** `feat/branch-register`
**PR title:** `feat: branch register with auto codes and lifecycle`

```text
TASK P3 — Cities and branch register. 3 steps; stop after each.

Read first: AGENTS.md, 06-state-machines.md §1, 07-business-rules.md BR-001, BR-002, BR-005, BR-010…BR-014, 08-data-model.md §3.2, §3.3, §3.5, 03-ambiguity-register.md AMB-12.

STEP 1 — Cities, ID sequences, branch model + code generation
- core.IdSequence(key PK, last_value) and core/ids.py next_value(key) using INSERT … ON CONFLICT DO NOTHING then SELECT … FOR UPDATE via the ORM (select_for_update) — must run inside the caller's transaction.
- City model (code ^[A-Z]{3}$ unique + check, name_en, name_ur) + a data migration seeding KHI, LHE, ISB, RWP, PEW, QTA, MUX, FSD, HYD, SKT with Urdu names.
- Extend Branch to the full 08 §3.3 schema; DB trigger blocking UPDATE of code; unique (city, lower(name_en)).
- branches/services.py create_branch(actor, data) → code BR-{CITY}-{NN} (2-digit minimum, grows naturally), status FORMING, audit branch.created.
- Tests: T-BRN-CODE-FORMAT, T-BRN-CODE-IMMUTABLE, T-BRN-NAME-UNIQUE, T-CITY-CODE, T-BRN-CODE-RACE (transaction=True, 10 threads creating KHI branches → BR-KHI-01..10, no duplicates).
Commit: feat(branches): add cities and branch register with generated codes

STEP 2 — Lifecycle transitions
- BRANCH_TRANSITIONS table: activate, pause (reason), resume, close (reason; guard: no unsent collections and no SUBMITTED/RESUBMITTED/RETURNED reports — implement the guard as a function that returns no blockers for now, with a TODO naming P6/P7 that the reviewer will see in the summary). opened_on/closed_on set; audit events per 06 §1. Invalid → InvalidTransition (→ 409).
- assignment service rejects assigning to CLOSED branches (BR-014).
- Tests: T-BRN-TRANSITIONS (every state × action pair), T-ASSIGN-CLOSED, audit rows present.
Commit: feat(branches): add branch lifecycle transitions with guards

STEP 3 — Screens + routes + permissions
- SA: list (filter city/status), detail (counts placeholders + history panel from audit), create/edit form, transition buttons with a confirm form (reason textarea where needed). FR/BL/HR: read-only list/detail scoped per matrix. City management page for SA.
- Register all routes in ROUTE_ACTIONS and the RBAC test registry.
- selectors.public_branches() returning FORMING/ACTIVE/PAUSED (BR-013) + test T-PUB-BRANCH-VISIBILITY (selector level; the public page comes in P10).
- Wire the "History" panel component (templates/partials/history.html) reading audit rows for an entity — reused later.
Commit: feat(branches): add branch register screens with scoped access

OUT OF SCOPE: public branch pages (P10), collections.
```

**PR #4 body:**
```markdown
## Summary
City lookup, branch register with concurrency-safe `BR-{CITY}-{NN}` codes, a Forming → Active ↔ Paused → Closed lifecycle with guards, Super Admin screens and scoped read access.

## Why
Brief: "Branch register: auto-generated branch codes and a status lifecycle". Growth outcome: adding a branch needs no code change.

## Tests
Code format/immutability/race, all transition pairs, close guards, scope.

## Traceability
REQ-050–056, BR-001, 002, 005, 010–014
```

---

## P4 — Volunteer applications → PR #5

**Branch:** `feat/volunteer-applications`
**PR title:** `feat: volunteer applications and HR approval`

```text
TASK P4 — Public application form and HR decision workflow. 3 steps; stop after each.

Read first: AGENTS.md, 07-business-rules.md BR-003, BR-004, BR-040…BR-055, 06-state-machines.md §2, 08-data-model.md §3.6–§3.9, 04-personas-journeys.md J4.1, J4.2, J6.1, J6.4, 16-ux-design-screens.md §4.2, §4.4.

STEP 1 — Application model + public form
- volunteers.Application per 08 §3.6 incl. check constraints. VolunteerRole + Team + Member models per 08 §3.7–3.9 (Member needed for accept; list screens come in P5). Data migration for volunteer roles (VOLUNTEER, TEAM_LEAD, COORDINATOR, TREASURER with Urdu names).
- ApplicationForm implementing BR-040…BR-050 exactly (phone normalisation to +923XXXXXXXXX; Unicode-letter name check using explicit ranges or the `regex` package — say which; age by clock.today()). Preferred-branch choices = ACTIVE/FORMING branches, re-validated on POST. Interests: published program slugs + "general" (programs don't exist until P10: use a constant list for now with a note).
- Spam guards (BR-051): hidden honeypot "website"; signed timestamp field (django.core.signing, salt "apply-form") with min 3 s, max 2 h; django-ratelimit 5/h and 20/day per IP using the DatabaseCache (createcachetable in start.sh/migrations note). Honeypot or timing failure → render the normal thanks page with a fake-looking reference but create nothing, and audit application.spam_blocked (no PII). Rate limit → 429 template.
- Service submit_application(): reference APP-YYYY-NNNNN, duplicate flag (BR-052), consent_at, ip_hash = sha256(ip + SECRET_KEY); audit application.submitted (actor anonymous).
- Pages: /<lang>/get-involved/ (form only for now, accessible markup per 14 §3: labels, aria-describedby, error summary with links) and /<lang>/get-involved/thanks/?ref=…
- Tests: T-APP-SUBMIT-OK; T-APP-VALIDATION-* boundaries (name 2/3/100/101, phone formats valid/invalid, age 15/16/17 without and with guardian/100/101, motivation 19/20/1000/1001, consent missing); T-APP-SPAM-HONEYPOT, -TIMING, -RATE; T-APP-DUP-FLAG; T-APP-NO-ENUM (duplicate and new submissions get identical response structure); T-APP-BRANCH-OPEN; T-APP-CONSENT.
Commit: feat(volunteers): add public application form with validation and spam guards

STEP 2 — HR decision services
- accept_application(actor, app_id, team_id, role_id): one transaction — select_for_update the application → require PENDING → member_id via ids.next_value("member:YYYY") → create Member (status ACTIVE, joined_on today, branch from application, team must belong to branch) → link → ACCEPTED, decided_by/at → audit application.accepted + member.created. decline_application(actor, app_id, reason 5–500) and reassign_branch(actor, app_id, branch_id). Scope: HR only for assigned branches (reassign requires the source application's branch in scope; the target may be any Active/Forming branch).
- Tests: T-APP-ACCEPT-ATOMIC (patch audit.record to raise after member insert → no member row, app still PENDING), T-APP-ACCEPT-RACE (two threads accept the same app → exactly one member, the other gets InvalidTransition), T-APP-TERMINAL, T-MEM-ID-FORMAT, T-MEM-ID-RACE (10 apps accepted concurrently → 10 unique sequential IDs), T-ID-REFS.
Commit: feat(volunteers): add HR review with atomic accept creating members

STEP 3 — HR screens
- Applications list (tabs Pending/Accepted/Declined, branch filter, duplicate badge), detail (all fields, duplicate panel linking the matched app/member, history), accept form (team + role selects filtered to the branch), decline form (reason), reassign form. SA read-only. Register routes + RBAC registry entries.
- Tests: scope (HR of KHI+LHE can't open an ISB application → 404), T-RBAC-SCOPE-APP.
Commit: feat(volunteers): add application review screens for HR leads

OUT OF SCOPE: member list/search (P5), Urdu translations (P11; strings must still be wrapped).
```

**PR #5 body:**
```markdown
## Summary
Public volunteer form with full server-side validation (Pakistani mobile, age rules, consent), spam protection (honeypot, signed timing, per-IP rate limit), duplicate flagging without enumeration, and an HR workflow where accepting creates a member with an `M-YYYY-NNNNN` ID atomically.

## Why
Deliverables 2 and 5; the Security row (spam, PII handling).

## Tests
Field boundaries, spam guards, atomic accept with fault injection, accept race, concurrent member IDs, scope.

## Traceability
REQ-030–039, REQ-060, BR-003, BR-004, BR-040–055
```

---

## P5 — Members → PR #6

**Branch:** `feat/members`
**PR title:** `feat: member records with search and filters`

```text
TASK P5 — Member records, teams, volunteer roles. 3 steps; stop after each.

Read first: AGENTS.md, 06-state-machines.md §6, 07-business-rules.md BR-055…BR-059, 08 §3.7–§3.9, 16 §4.5.

STEP 1 — Teams and volunteer roles management
- HR: team list/create/rename/deactivate per assigned branch (unique per branch, case-insensitive). SA: volunteer roles list/create/edit/deactivate. Services + audit (team.created/updated).
- Composite FK (team_id, branch_id) → teams(id, branch_id) per 08 §3.9 (RunSQL if Django can't express it; explain in the summary).
- Tests: T-TEAM-UNIQUE, T-MEM-TEAM-BRANCH.
Commit: feat(volunteers): add teams and volunteer roles

STEP 2 — Member list with search, filters, pagination
- selectors.search_members(user, params): scoped; q matches full_name/email/member_id case-insensitively and phone by digits; filters branch, team, role, status, joined_from/joined_to (AND); sort newest by default, sortable by name/joined; Paginator 25.
- MemberListView with a GET filter form that keeps parameters in pagination links; responsive table (card mode under 640px via CSS).
- Tests: T-MEM-SEARCH-* (each field, combined filters, scope: BL/HR see only assigned branches, FR/CE 403), T-MEM-PAGINATION.
Commit: feat(volunteers): add member list with search, filters and pagination

STEP 3 — Member detail, edit, status transitions
- Detail with history panel; edit form (team, role, contact fields — never member_id/branch/status); status actions per 06 §6 (deactivate, reactivate, mark left with date, SA-only reinstate with reason). Audit member.updated / member.status_changed / member.reinstated. Partial unique index lower(email) WHERE status <> 'LEFT' (BR-055).
- Tests: T-MEM-STATUS (every transition, left_on rules), T-MEM-EMAIL-UNIQUE, T-SEC-MASS-ASSIGN (POSTing status/member_id to the edit form is ignored).
Commit: feat(volunteers): add member detail, editing and status transitions

OUT OF SCOPE: member CSV export (P9).
```

**PR #6 body:**
```markdown
## Summary
Teams (per branch) and volunteer roles (global), a scoped member list with search, filters and pagination, member editing and a status lifecycle (Active/Inactive/Left, SA reinstate).

## Traceability
REQ-061–065, BR-055–059
```

---

## P6 — Collections and transfers → PR #7

**Branch:** `feat/collections`
**PR title:** `feat: collections, 7-day lock and transfers`

```text
TASK P6 — Offline collections with the 7-day lock, void, and transfers to the main account. 4 steps; stop after each.

Read first: AGENTS.md, 06-state-machines.md §4, 07-business-rules.md BR-060…BR-071, BR-140, 08 §3.10–§3.11, 03-ambiguity-register.md AMB-04, AMB-05, 16 §4.6.

STEP 1 — Collection model + create
- finance.Collection per 08 §3.10 with all check constraints and indexes (incl. the partial unsent index). Reference COL-{branch_code}-{NNNNN}.
- CollectionForm (date, amount, method, receipt_no, collected_by member of the same branch, source_note); service create_collection enforcing BR-060…BR-063, BR-066, and BR-065 via a function week_is_closed(branch, date) that returns False until P7 replaces it (name the P7 hook in the summary).
- Tests: T-COL-CREATE, T-COL-AMOUNT, T-COL-METHOD, T-COL-DATE-RANGE (today−7 ok, today−8 rejected, tomorrow rejected; PKT dates), T-COL-RECEIPT-UNIQUE, T-COL-BRANCH-ACTIVE.
Commit: feat(finance): add offline collection entry with validation

STEP 2 — Lock, edit, void
- Collection.lock_at = created_at + timedelta(days=rules.get("collection_lock_days")); is_locked uses clock.now(); derived state property (VOIDED/SENT/LOCKED/OPEN) per 06 §4.
- services.assert_editable(collection) — single place checking voided, sent, locked, week closed; update_collection and void_collection (reason 5–300) use it; denied attempts write collection.edit_denied and return 409 with a translated reason ("Entry locked on <PKT datetime>").
- List screen: filters (date range, method, state), totals row, state badges with a lock countdown ("locks in 3 days").
- Tests: T-COL-LOCK-BEFORE (6 d 23 h 59 m 59 s editable), T-COL-LOCK-AT (exactly 7 d → locked, edit and void both 409), T-COL-LOCK-AFTER, T-COL-LOCK-CONFIG (setting 3 → locks at 3 d), T-COL-VOID (excluded from totals), audit before/after diff on edit.
Commit: feat(finance): lock collections seven days after entry

STEP 3 — Transfers (mark sent)
- finance.Transfer per 08 §3.11; create_transfer(actor, branch, collection_ids, transfer_date, bank_reference, note): select_for_update the chosen collections; enforce BR-069; set transfer_id; total = sum; audit transfer.created + collection.sent per entry. DB trigger rejecting UPDATE of amount/collection_date/method/branch_id on collections with transfer_id set (BR-070); trigger rejecting UPDATE on transfers.
- Screen: unsent filter with checkboxes → transfer form showing the running total; transfer list/detail.
- Tests: T-XFER-RULES (mixed branch, voided, already sent, empty selection, date before a collection date), T-XFER-DOUBLE (two concurrent transfers over the same collection → one fails), T-XFER-IMMUTABLE.
Commit: feat(finance): add void and transfer to main account

STEP 4 — Wire branch close guard + permissions
- Replace the P3 close guard stub: blockers include unsent collections (count + total). Register all routes; RBAC registry entries; scope tests (BL of KHI → LHE collection 404; FR read-only; HR/CE 403).
Commit: test(finance): cover collection scope and branch close guard

OUT OF SCOPE: adjustment entries (BR-067, Should — only if time allows later), weekly reports.
```

**PR #7 body:**
```markdown
## Summary
Offline collection logging (cash, cheque, bank deposit — no online payments), a computed 7-day lock from entry time (configurable, no unlock), void with reason, and transfers to the main account that mark collections as sent and immutable.

## Why
Deliverable 7 and the data behind the "not yet sent to the main account" dashboard list.

## Tests
Lock boundaries with a frozen clock, configurable lock days, transfer rules and race, DB-level immutability, scope.

## Traceability
REQ-070–077, BR-060–071
```

---

## P7 — Weekly reports → PR #8

**Branch:** `feat/weekly-reports`
**PR title:** `feat: weekly report workflow with locking`

```text
TASK P7 — Weekly report workflow (Gate 2). 4 steps; stop after each.

Read first: AGENTS.md, 06-state-machines.md §3 (all of it), 07-business-rules.md BR-065, BR-080…BR-090, 08 §3.12–§3.13, 16 §4.7, 17-test-strategy.md §3.2, 15-devops §6.4 (the PR description shows the expected scope).

STEP 1 — Models, registry, lazy drafts, aggregates
- WeeklyReport + WeeklyReportLine per 08 with constraints (week_start isodow=1, week_end = start+6, unique (branch, week_start), locked_at check). RunSQL triggers: weekly_reports BEFORE UPDATE/DELETE when OLD.status='LOCKED' → raise; weekly_report_lines BEFORE UPDATE/DELETE when parent LOCKED → raise.
- finance/report_fields.py REPORT_FIELDS registry (activities required 10–2000, volunteer_hours int 0–10000 required, issues optional ≤2000) and a form built from it.
- week_bounds(date) helper (Mon–Sun, PKT). report_aggregates(branch, week_start) per BR-083 (pure query function returning a dict of Decimals/ints).
- ensure_drafts(branch): for an ACTIVE branch, get_or_create DRAFT reports from the week containing opened_on up to the current week (IntegrityError-safe), audit report.drafted (actor system) only when created. Management command generate_weekly_drafts.
- Tests: T-RPT-WEEK, T-RPT-UNIQUE, T-RPT-AUTODRAFT, T-RPT-AUTODRAFT-IDEMPOTENT (twice → same count, one audit row each), T-RPT-AGGREGATES (voided excluded, month-spanning week, by_method).
Commit: feat(finance): add weekly report auto-drafting and aggregates

STEP 2 — Transitions + snapshot + lock
- REPORT_TRANSITIONS table (submit, return, resubmit, approve) and one transition() function per 06 §3: select_for_update, state check, expected_revision check for return/approve (BR-088), guards (week ended unless allow_submit_current_week; narrative valid; return comment 5–1000). submit/resubmit: revision += 1, snapshot = aggregates + narrative + lines, insert WeeklyReportLine rows for the new revision, snapshot_hash = sha256(canonical JSON). approve: APPROVED + audit report.approved, then LOCKED + locked_at + audit report.locked in the same transaction.
- Replace the P6 week_is_closed stub: True when the report for that branch-week is SUBMITTED/RESUBMITTED/APPROVED/LOCKED.
- Branch close guard: add open-report blockers.
Commit: feat(finance): add submit, return, resubmit and approve transitions

STEP 3 — Screens per state
- Reports list (BL scoped, calls ensure_drafts on load; FR/SA all with branch/status/week filters), review queue for FR (SUBMITTED + RESUBMITTED, oldest first), detail page rendering each state as in 16 §4.7: status timeline from audit, live totals (DRAFT/RETURNED) or snapshot (others), lines table, narrative form (BL in DRAFT/RETURNED), review panel (FR), returned-comment banner, lock banner. Hidden input expected_revision. Register routes + RBAC registry.
Commit: feat(finance): add weekly report screens for branch leads and finance

STEP 4 — Gate-2 test suite
- test_t_rpt_lifecycle exactly as 17 §3.2 (clock fixture; assert the 6 ordered audit actions for the entity, each with actor role and request_id; verify_chain ok; raw SQL UPDATE on the locked report raises; editing a collection in that week → 409).
- Negative tests: BL can't approve, FR can't submit, stale revision → 409, return without comment → form error, submit before week end → error, T-RPT-CONCURRENT-REVIEW (two threads approve → one wins), T-RPT-LOCKED-IMMUTABLE, T-RPT-SNAPSHOT (changing a collection after submit doesn't change the snapshot), T-COL-WEEK-CLOSED.
Commit: test(finance): add full report lifecycle test with audit assertions

OUT OF SCOPE: PDF export (P9), dashboard (P8).
```

**PR #8 body:** use the sample in `15-devops-ci-cd-git.md` §6.4.

---

## P8 — Sample data + dashboard → PR #9

**Branch:** `feat/dashboard-sample-data`
**PR title:** `feat: head office dashboard and sample data`

```text
TASK P8 — Authored sample data (CSV), importer, demo logins, dashboard (Gate 1). 4 steps; stop after each.

Read first: AGENTS.md, 09-dashboard-and-seed-data.md (ALL — it is the specification and the expected values), 05-rbac-matrix.md §3.7, 16 §4.8, 11-security.md §2 (demo credentials row).

STEP 1 — sample_data/*.csv
- Create CSV files exactly reproducing 09 §3 (cities, branches, users, members, applications, collections incl. created_at timestamps with +05:00 offset, transfers with collection refs, weekly_reports with target status and revision and history, content placeholder rows). Use natural keys, ISO dates, dot decimals, UTF-8 with header. Add sample_data/README.md describing each file and its columns, and stating the data is fictional and authored for this submission.
- Double-check the CSV totals against 09 §4 and list the per-file row counts in the summary.
Commit: feat(sample-data): add authored fictional sample dataset as CSV

STEP 2 — Importer + seed_demo
- import_sample_data <dir> [--mapping YAML]: validates headers (clear error listing missing/unknown columns), loads in dependency order inside one transaction, uses services where they exist but allows historical timestamps through an explicit `as_of`/clock override (document how: e.g. time_machine-style clock context in core.clock used only by the importer). Reports are built by replaying transitions (draft → submit → [return → resubmit] → approve/lock) under the clock at the CSV timestamps, so audit rows and the hash chain are genuine and ordered.
- seed_demo [--if-empty] [--reset]: requires DEMO_MODE=true and DEMO_PASSWORD; calls the importer on sample_data/; sets demo users' passwords and is_demo=True; marks the system_settings key "demo_seeded". --reset (DEMO_MODE only): `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` → `migrate` → import. `flush` won't work because the audit table's TRUNCATE trigger blocks it, which is intended; dropping the schema removes the triggers along with the tables, so audit protection is never switched off for live data. Explain this in the summary.
- SA "Reset demo data" button (POST, DEMO_MODE only, audited demo.reset).
- Tests: T-SEED-IDEMPOTENT, T-SEED-DEMO-ONLY (no DEMO_MODE → command refuses), T-SEED-USERS (5 role logins succeed and land on their homes), importer header error test.
Commit: feat(seed): add sample data importer and demo seed with test logins

STEP 3 — KPI functions + dashboard
- apps/dashboard/kpis.py: one pure function per KPI K1–K10, TR1, TR2, L1, L2 with signature (period: (year, month), as_of: datetime, branch_ids: list[int] | None) per 09 §2 formulas. No caching.
- Head-office dashboard (SA, FR): period selector (default current month via clock), tiles, two Chart.js charts (vendored static/vendor/chart.umd.min.js; data passed with json_script; a small static/js/dashboard.js — no inline script), unsent table (L1) and branch table (L2). Branch dashboard (BL, scoped). HR overview with pending counts (HR, scoped). Empty states. Acceptance rate shows "—" when there are no decisions.
- Register routes + RBAC registry.
Commit: feat(dashboard): add head office KPIs, trends and unsent list

STEP 4 — Gate-1 tests
- test_t_dash_seed: load sample data, freeze clock at 2026-10-31 23:00 PKT, assert EVERY value in 09 §4.1, §4.2, §4.3, §4.4, §4.5, §4.7 with Decimal equality. T-DASH-TRENDS (12 zero-filled points), T-DASH-REALTIME (approve R9 → K2 58,250.50, K3 15,000.00, awaiting 0), T-RBAC-SCOPE-DASH, T-GROWTH-N-BRANCHES (50 branches × 3 collections; totals correct; django_assert_max_num_queries(25) on the dashboard view).
- If any expected value from 09 doesn't match, DO NOT change the expected value: report the discrepancy with your calculation so the owner can decide.
Commit: test(dashboard): assert expected values from sample data
```

**PR #9 body:**
```markdown
## Summary
Authored fictional sample dataset (CSV) with a validating importer that replays real workflow transitions (so the audit trail is genuine); `seed_demo` with one test login per role; head-office dashboard with KPIs, 12-month trends, unsent-collections list and per-branch table; branch and HR dashboards.

## Why
Gate 1: "When the sample data is loaded, the dashboard must show the correct expected values." The hand-calculated values are in `docs/planning/09-dashboard-and-seed-data.md` §4 and asserted by tests.

## Tests
Every expected value at as-of 2026-10-31, trends, real-time update after approval, scope, 50-branch growth with bounded queries.

## Traceability
REQ-006, REQ-090–095, BR-090
```

---

## P9 — Exports → PR #10

**Branch:** `feat/exports`
**PR title:** `feat: CSV and PDF exports`

```text
TASK P9 — CSV and PDF exports. 3 steps; stop after each.

Read first: AGENTS.md, 13-exports.md (all), 12-i18n-rtl.md §9.

STEP 1 — CSV exports
- apps/exports/registry.py: EXPORTS = {code: Export(action, queryset_fn(user, params), columns [(header_msgid, getter)])}. One generic CSV view: permission check, scoped queryset, the same filters as the list screens, utf-8-sig, formula-injection guard for text cells (numeric amounts written as numbers), StreamingHttpResponse, filename pattern from 13 §2, audit export.csv with metadata, ratelimit 30/h/user.
- Exports X1, X2, X3, X5-CSV, X6, X7 from 13 §1. Add "Export CSV" buttons on the corresponding list screens.
- Tests: T-EXP-CSV-COLLECTIONS, T-EXP-CSV-INJECTION, T-EXP-CSV-UR (headers translated when lang=ur — will pass fully after P11; assert BOM and decoding now), T-RBAC-SCOPE-EXP, T-AUD-EXPORT.
Commit: feat(exports): add CSV exports with BOM and formula guard

STEP 2 — PDF exports
- WeasyPrint rendering of templates/pdf/weekly_report.html (X4) and monthly_summary.html (X5) with static/css/pdf.css (@page A4, page counter, repeated thead, rows don't break). Fonts via @font-face pointing at static files (base_url = STATIC_ROOT or finders). Watermark "DRAFT — NOT APPROVED" unless LOCKED. Footer: generated at (PKT), by, "Demo data" in DEMO_MODE. Audit export.pdf.
- Tests: T-EXP-PDF-REPORT (pypdf text contains branch code, 25,250.50 and the Locked label for R7), T-EXP-PDF-WATERMARK, summary PDF smoke test. Add pypdf to dev requirements.
Commit: feat(exports): add weekly report and monthly summary PDFs

STEP 3 — Scope/permission coverage
- RBAC registry entries for every export route; CE 403, out-of-scope 404; row-count limit for the summary (2,000 lines → message suggesting CSV).
Commit: test(exports): cover export scope and content
```

**PR #10 body:**
```markdown
## Summary
Generic, scoped, audited CSV exports (UTF-8 BOM, formula-injection guard) for collections, unsent collections, reports, monthly summary, members and audit log; WeasyPrint PDFs for the weekly report (official copy with snapshot hash and draft watermark) and the monthly head-office summary.

## Traceability
REQ-100–104
```

---

## P10 — Public site + CMS → PR #11

**Branch:** `feat/public-site-cms`
**PR title:** `feat: public website and content manager`

```text
TASK P10 — Content manager and the seven public pages. 4 steps; stop after each.

Read first: AGENTS.md, 06-state-machines.md §5, 07-business-rules.md BR-120…BR-123, 08 §3.14–§3.15, 16-ux-design-screens.md §1.1, §4.1, §4.10, §5, 14-performance-a11y-seo.md §2–§4.

STEP 1 — CMS models + services
- ContentItem + ContentTranslation per 08. Services: create/update (working copy, sets has_unpublished_changes when PUBLISHED), publish (guard BR-121; copies working translations into published_snapshot; published_at), unpublish, archive, restore — each audited. Markdown → HTML with `markdown` then `nh3` allow-list (BR-123), done on save; template filter `render_cms` is the ONLY place `|safe`-equivalent output is allowed (mark_safe on nh3 output).
- Tests: T-CMS-STATES, T-CMS-LIVE-SNAPSHOT (edit after publish doesn't change the public output), T-CMS-PUBLISH-GUARD, T-CMS-SLUG, T-CMS-EVENT-DATES, T-SEC-XSS-CMS (script, onerror, javascript: links stripped).
Commit: feat(cms): add content items with draft, publish and archive

STEP 2 — Content editor screens
- CE/SA: list with type tabs and status/"unpublished changes" badges; editor with EN | اردو tabs (CSS-only tabs using radio inputs or <details>; Urdu inputs dir="rtl" lang="ur"); event fields; preview page; action buttons. Register routes + RBAC registry.
Commit: feat(cms): add content editor with English and Urdu tabs

STEP 3 — Seven public pages
- Views + templates for Home, About, Programs (+detail), Branches (+detail, using public_branches(), filter by city), Events (+detail; upcoming/past), Get Involved (existing form + offline donation note — no payment UI), Contact, Privacy. Content comes only from published snapshots. Header nav with current-page aria-current, language switcher (POST set_language with the translated `next`), mobile nav via <details>. Zero JavaScript on public pages. Images: <picture> with width/height, lazy below the fold.
- Add CMS rows to sample_data/content.csv (3 programs incl. 1 DRAFT, 3 events with dates relative to import day, page sections) in EN and UR, and import them.
- Tests: T-PUB-PAGES (7 pages × en/ur → 200), T-PUB-NO-LEAK, T-CMS-PUBLIC-ONLY-PUBLISHED, T-PUB-BRANCH-VISIBILITY (page level).
Commit: feat(public): add seven public pages rendered from CMS

STEP 4 — SEO
- Per-page title/meta description, canonical, hreflang en/ur/x-default, Open Graph; sitemap.xml (i18n alternates) and robots.txt per 14 §4; staff pages get noindex. Tests: T-PUB-SEO.
Commit: feat(public): add sitemap, robots and meta tags
```

**PR #11 body:**
```markdown
## Summary
Content manager (Programs, Events, Page sections) with Draft/Published/Archived states, a live snapshot so edits don't go public until re-published, and sanitised Markdown. Seven public pages rendered from published content, a branch directory filtered by status, and SEO basics (meta, hreflang, sitemap, robots).

## Traceability
REQ-020–027, REQ-110–114, BR-013, BR-120–123
```

---

## P11 — Urdu and RTL → PR #12

**Branch:** `feat/i18n-urdu`
**PR title:** `feat: English/Urdu with right-to-left layout`

```text
TASK P11 — Urdu localisation and RTL. 4 steps; stop after each.

Read first: AGENTS.md, 12-i18n-rtl.md (all), 14 §2 (fonts).

STEP 1 — RTL layout pass
- Audit main.css and pdf.css: logical properties only (add a CI grep step in ci.yml lint job for margin-left|margin-right|padding-left|padding-right|left:|right:|text-align: left|text-align: right outside a vendor dir). Directional icon flip, <bdi> around codes/phones/emails/amounts in templates, numeric columns text-align: end. Chart.js rtl options when LANGUAGE_BIDI.
- Locale stylesheet static/css/ur.css loaded only when LANGUAGE_CODE == "ur": @font-face Noto Naskh Arabic regular/bold woff2 (subset files in static/fonts/ + OFL licence text), font-display: swap, preload regular; Urdu line-height 1.8, base 1.0625rem.
- Provide the exact pyftsubset command used to subset the fonts in docs (scripts/subset_fonts.sh) — run it and commit the outputs.
- Tests: T-I18N-DIR, T-I18N-SWITCH.
Commit: feat(i18n): add Urdu locale with RTL layout

STEP 2 — Translate all UI strings
- Run makemessages -l ur; translate EVERY msgid in locale/ur/LC_MESSAGES/django.po into natural, polite Urdu (آپ form), keeping placeholders identical. Formats file formats/ur/formats.py (date format "j F Y", Western digits). money filter output per 12 §6.
- List in the summary any terms you were unsure about so the owner can review them with a fluent speaker.
Commit: feat(i18n): translate all UI strings to Urdu

STEP 3 — Urdu PDFs and CSV headers
- PDF templates honour lang (dir="rtl", Naskh font embedded); CSV headers translated.
- Tests: T-EXP-PDF-UR (pypdf text contains a known Urdu label), T-EXP-CSV-UR, T-I18N-VALIDATION-UR.
Commit: feat(exports): render Urdu PDFs with Naskh font

STEP 4 — Parity test + CI check
- T-I18N-PARITY with polib: 100% translated, no fuzzy/obsolete entries, placeholder sets equal; a CI step that runs makemessages into a temp copy and fails if new msgids are missing from the committed .po.
Commit: test(i18n): add translation parity and direction tests
```

**PR #12 body:**
```markdown
## Summary
Full Urdu UI with right-to-left layout via CSS logical properties, a subset Noto Naskh Arabic font loaded only on Urdu pages, localised dates and money, Urdu PDFs shaped correctly by WeasyPrint/HarfBuzz, and a translation parity test in CI.

## Traceability
REQ-021, REQ-130–134
```

---

## P12 — E2E + Lighthouse → PR #13

**Branch:** `test/e2e-lighthouse`
**PR title:** `test: E2E smoke tests and Lighthouse gate`

```text
TASK P12 — End-to-end smoke tests, accessibility checks and Lighthouse CI. 3 steps; stop after each.

Read first: AGENTS.md, 17-test-strategy.md §3.5, 14-performance-a11y-seo.md §3, §6.

STEP 1 — Playwright E2E
- tests/e2e with pytest-playwright (Chromium) against a BASE_URL (default the compose stack). Implement E2E-01 … E2E-05 from 17 §3.5. Mark them with @pytest.mark.e2e and exclude them from the default pytest run.
- axe-core accessibility check on the 7 public pages × 2 locales (inject the axe script from a vendored file; fail on serious/critical).
- E2E-LIVE: the same smoke checks parameterised by BASE_URL for a manual run against Render (no writes except one application submit; document this).
Commit: test(e2e): add smoke journeys with Playwright and axe

STEP 2 — CI jobs
- ci.yml: e2e job (needs docker; starts the compose stack with DEMO_MODE seed; runs pytest -m e2e; uploads traces on failure). lighthouse job with lighthouserc.json from 14 §6 (disable only the is-on-https audit in CI, documented in a comment).
Commit: ci: add E2E and Lighthouse CI jobs

STEP 3 — Fix findings + raise coverage gate
- Fix every a11y/Lighthouse issue found on the measured pages (contrast, labels, heading order, image sizes). Raise --cov-fail-under to 70 if current coverage ≥ 72%; otherwise add tests to the lowest-covered service modules first and report the numbers.
Commit: ci: raise coverage threshold to 70%
```

**PR #13 body:**
```markdown
## Summary
Playwright smoke tests for the critical journeys (apply → accept, full report lifecycle, Urdu RTL, dashboard values), axe accessibility checks on all public pages in both languages, a Lighthouse CI gate (≥ 0.9 in all four categories on five pages), and the coverage gate raised to 70%.

## Traceability
REQ-150, REQ-156, REQ-157
```

---

## P13 — Security hardening + performance → PR #14

**Branch:** `chore/security-hardening`
**PR title:** `chore: security hardening and performance`

```text
TASK P13 — Security hardening and performance. 3 steps; stop after each.

Read first: AGENTS.md, 11-security.md (all), 14-performance-a11y-seo.md §2.

STEP 1 — Headers, CSP, cookies
- django-csp policy exactly as 11 §2 (no unsafe-inline); Permissions-Policy header via a small middleware; confirm __Host- cookie names work behind Render's proxy; ensure no inline scripts or styles remain anywhere (grep and fix).
- Tests: T-SEC-HEADERS, T-SEC-COOKIES, T-SEC-CSRF (enforce_csrf_checks client), T-SEC-ERRORS (DEBUG=False 404/500 are generic and localised), T-SEC-SQLI, T-SEC-XSS-REFLECT, T-LOG-NO-PII.
Commit: feat(security): add CSP and strict security headers

STEP 2 — Self-audit against OWASP
- Walk every row of 11 §1 and verify the control exists in code; produce docs/security.md (OWASP mapping with file references and test names, threat model, known limitations incl. the DB-owner trigger caveat). Fix any gap found and list it in the summary. Add CI grep checks: no csrf_exempt, no `.save(` in views.py, no `objects.get(` in views.py, no `|safe` outside the CMS filter template.
Commit: fix(security): close gaps found in OWASP self-review

STEP 3 — Performance
- Optimise images (AVIF/WebP + fallback, explicit sizes), make sure cache headers are immutable for hashed static files, check query counts on public pages (≤ 5) with django_assert_max_num_queries, confirm zero JS on public pages.
Commit: perf(public): optimise images, fonts and query counts
```

**PR #14 body:**
```markdown
## Summary
Strict CSP without inline scripts, Permissions-Policy, verified cookie flags, CSRF/XSS/SQLi/error-handling tests, an OWASP Top 10 self-review documented in docs/security.md, CI guard rails against unsafe patterns, and public-page performance work.

## Traceability
REQ-140–147, REQ-156
```

---

## P14 — Documentation → PR #15

**Branch:** `docs/handover`
**PR title:** `docs: architecture decisions, API docs and handover guide`

```text
TASK P14 — Documentation folder. 3 steps; stop after each. Write in clear, plain English; describe what the code ACTUALLY does — read the code; don't copy the plan where the implementation differs (list such differences in the summary).

Read first: AGENTS.md, 18-docs-demo-video-qa.md §1, §2, §4, 10-architecture-and-stack.md §9.

STEP 1 — ADRs and architecture
- docs/adr/0001…0012 per 10 §9 (Context · Decision · Consequences · Alternatives considered; dated). docs/architecture.md with Mermaid C4 context/container, module map, request lifecycle, ER diagram matching the real models. docs/data-model.md, docs/business-rules.md (BR catalogue with "enforced in <file>" references).
Commit: docs: add ADRs and architecture overview

STEP 2 — API reference + permission table + test
- Management command export_routes writes docs/api.md: every URL pattern with method(s), action, allowed roles (from PERMISSIONS), parameters, success/error responses. docs/openapi.yaml for the JSON endpoints (/health, dashboard data, and the internal drafts endpoint if it exists). Regenerate docs/permissions.md. Test T-DOC-ROUTES (generated == committed).
Commit: docs: generate API reference and permission table from code

STEP 3 — Handover, testing, i18n, credits, README
- docs/handover.md per 18 §4, docs/testing.md, docs/i18n.md, docs/credits.md (pip-licenses --format=markdown output + Chart.js MIT + Noto OFL + axe MPL), docs/README.md index. Full README per 18 §2 (leave the live URL, password value, coverage % and final SHA as clearly marked placeholders for the owner to fill in).
Commit: docs: complete README, handover guide and credits
```

**PR #15 body:**
```markdown
## Summary
Docs folder: 12 ADRs, architecture with C4 and ER diagrams, a generated API reference and permission table (CI-checked against the code), handover guide, testing and i18n guides, dependency credits, and the full README with test logins and a judge quick path.

## Traceability
REQ-005, REQ-007, REQ-011
```

---

## P15 — Twist task template → PR #16

**Branch:** `feat/<twist-slug>`  ·  **PR title:** `feat: <twist summary>`

```text
TASK P15 — Surprise twist: <paste the twist text verbatim>.

Read first: AGENTS.md, docs/planning/20-risks.md §2 (twist-readiness), and the planning files for the affected area.

STEP 1 — Impact analysis ONLY (no code): list the affected models, services, permissions, templates, translations, tests and docs; propose the smallest design that fits the existing extension points (permission matrix, transition tables, REPORT_FIELDS, rules settings, export registry, KPI functions); estimate hours. Stop and wait for approval.
STEP 2 — Implement with tests (including RBAC registry entries, audit events and Urdu strings).
STEP 3 — Update docs (ADR "0013-twist-…", api.md/permissions.md regenerated, README feature table).
Commits: feat(<area>): <what> · test(<area>): <what> · docs: document <twist>
```

---

## P16 — Release → PR #17

**Branch:** `chore/release-1.0.0`  ·  **PR title:** `chore: release v1.0.0`

```text
TASK P16 — Release preparation. 2 steps; stop after each. No feature changes.

STEP 1 — Version + changelog: VERSION file 1.0.0 shown in the footer and in /health as "release"; CHANGELOG.md summarising merged PRs #1–#16 (read git log --merges); make sure ruff, pytest (with coverage), e2e and makemigrations --check all pass; report the final coverage %.
Commit: chore(release): bump version to 1.0.0 and update changelog

STEP 2 — Final docs pass: check README placeholders are listed for the owner; check every link in docs/ resolves; check AI-USAGE.md has a row for every PR (list the missing ones for the owner to fill in — don't invent entries).
Commit: docs: finalise AI-USAGE log and release notes
```
After merge (you): wait for CI green and the Render deploy → `/health` shows the SHA → `git tag -a v1.0.0 -m "ShipLens 1.0 submission"` → push the tag → GitHub Release → copy the full SHA into the form → run the final checklist in `19-…` §8.

---

## §R — Review prompt (use any time)

```text
Explain the changes you just made as if I have to defend them to a judge in a live demo. For each changed file: what it does, why it is written this way, what would break if it were removed, and which planning rule (REQ/BR ID) it implements. Then list the 3 questions a judge is most likely to ask about this code with short answers. Do not change any code.
```

## §F — Fix-CI prompt

```text
CI failed on job <name>. Here is the log: <paste>. Diagnose the root cause, explain it in 2–3 sentences, and propose the smallest fix. Don't weaken tests, coverage thresholds, lint rules or security checks to make CI pass. Apply the fix only after explaining it; then stop and print the step summary.
```
