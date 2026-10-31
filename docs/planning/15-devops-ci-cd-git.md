# 15 — DevOps, CI/CD and Git Workflow

## 1. Dockerfile (multi-stage, non-root) — design
```text
Stage 1 "builder"  python:3.12-slim-bookworm
  - apt: build-essential (only here)
  - pip install --require-hashes -r requirements.txt into /opt/venv
Stage 2 "runtime"  python:3.12-slim-bookworm
  - apt (no-install-recommends): libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libffi8
    (Noto font files are vendored in static/fonts; no curl needed — the healthcheck uses Python)
  - COPY --from=builder /opt/venv ; COPY app
  - ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=config.settings.prod
  - RUN compilemessages && collectstatic --noinput (with a build-time dummy SECRET_KEY)
  - RUN useradd --uid 10001 --no-create-home app ; USER app
  - EXPOSE 8000
  - HEALTHCHECK --interval=30s --timeout=5s --start-period=40s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"
  - ENTRYPOINT ["./bin/start.sh"]   # migrate --noinput; [seed_demo --if-empty if DEMO_MODE]; exec gunicorn
```
Target image < 400 MB. `.dockerignore` excludes `.git`, `tests`, `docs`, `node_modules`, `.env*`.

## 2. `/health` endpoint
`GET /health` (no auth, no i18n prefix, excluded from route-registry auth, not rate-limited, `Cache-Control: no-store`):
```json
{ "status": "ok", "db": "ok", "version": "<GIT_SHA short>", "time": "2026-10-31T18:00:00Z" }
```
- DB check: `SELECT 1` with 2 s timeout. On failure → **503** `{ "status": "degraded", "db": "error" }` (no exception text).
- `version` from env `RENDER_GIT_COMMIT` (Render provides it) or build arg `GIT_SHA`.
- Tests: `T-OPS-HEALTH`, `T-OPS-HEALTH-DBDOWN` (mock cursor raising).

## 3. docker-compose (local dev)
Services: `db` (postgres:16-alpine, healthcheck `pg_isready`, volume), `web` (build ., `runserver` override, bind mount, env from `.env`, depends_on db healthy). `make up`, `make test`, `make seed` wrappers (or `just`). Same image as prod with dev command override.

## 4. GitHub Actions workflows

### 4.1 `ci.yml` — on `pull_request` and `push` to `main`
| Job | Steps | Required check? |
|---|---|---|
| `lint` | checkout → setup-python 3.12 (pip cache) → `ruff check` → `ruff format --check` → CSS logical-property grep → `csrf_exempt`/`.save(` in views grep | ✓ |
| `test` | service `postgres:16` (health-cmd pg_isready) → install → `manage.py check --deploy --fail-level WARNING` (prod settings w/ dummy env) → `makemigrations --check --dry-run` → i18n check → `pytest --cov=apps --cov-report=xml --cov-report=term-missing --cov-fail-under=90` → upload coverage artifact → coverage summary to job summary | ✓ |
| `security` | `pip-audit -r requirements.txt` → `gitleaks/gitleaks-action` | ✓ |
| `docker` | `docker build --build-arg GIT_SHA=$GITHUB_SHA` → `docker compose -f docker-compose.ci.yml up -d` → wait for healthy → `curl -fsS localhost:8000/health` → `docker run --rm image id -u` ≠ 0 | ✓ |
| `e2e` (needs docker) | start stack with seed → `pytest tests/e2e --browser chromium` (4 smoke journeys + axe) | ✓ (main + PRs labelled `e2e`; required from 30 Oct) |
| `lighthouse` (needs docker) | LHCI per `14-…` §6 | advisory until 31 Oct, then required |

### 4.2 `codeql.yml` — weekly + on PR (Python + JS). 
### 4.3 `dependabot.yml` — pip, github-actions, docker; weekly.
### 4.4 Optional `drafts.yml` — `schedule: cron '30 19 * * 0'` (Mon 00:30 PKT) → `curl -X POST -H "Authorization: Bearer $DRAFTS_TOKEN" $APP_URL/internal/generate-drafts` (OPT-06).

Pin third-party actions to commit SHAs; `permissions: contents: read` at workflow level.

## 5. Render

### 5.1 `render.yaml` (Blueprint) — design
```yaml
# illustrative
services:
  - type: web
    name: shiplens-web
    runtime: docker
    plan: free            # switch to starter for judging window (Q-05)
    region: singapore     # closest to Pakistan
    healthCheckPath: /health
    autoDeployTrigger: checksPass   # deploy main only after GitHub checks pass
    envVars:
      - key: DATABASE_URL
        fromDatabase: { name: shiplens-db, property: connectionString }
      - key: SECRET_KEY
        generateValue: true
      - key: DJANGO_ALLOWED_HOSTS
        value: shiplens-web.onrender.com
      - key: CSRF_TRUSTED_ORIGINS
        value: https://shiplens-web.onrender.com
      - key: DEMO_MODE
        value: "true"
      - key: DEMO_PASSWORD
        sync: false       # set manually in dashboard
      - key: WEB_CONCURRENCY
        value: "2"
databases:
  - name: shiplens-db
    plan: free            # expires 30 days after creation on free plan -> see caveats
    postgresMajorVersion: "16"
    region: singapore
```

### 5.2 Migrations and seed on deploy
- Pre-deploy commands and Render Shell are **paid-only**; so `bin/start.sh` runs `python manage.py migrate --noinput` before gunicorn (safe: single instance; migrations are additive). On paid plan, move to `preDeployCommand`.
- Seed: `seed_demo --if-empty` runs at start only when `DEMO_MODE=true` (idempotent; checks a marker in `system_settings`). Documented manual equivalent locally: `docker compose run web python manage.py seed_demo --reset`.

### 5.3 Free-tier caveats and mitigations
| Caveat | Impact on judging | Mitigation |
|---|---|---|
| Web service sleeps after 15 min idle; ~30–60 s cold start | Judge sees spinner; Lighthouse Performance tanks | (a) Upgrade to **Starter ($7/mo) for 1 Nov – 30 Nov** (recommended); (b) else GitHub Actions cron ping `/health` every 10 min (best-effort, GH cron can be delayed); README note "first load may take up to a minute". |
| Free Postgres **expires 30 days after creation** (data deleted after grace) | DB created 24 Oct dies ~23 Nov — inside live-demo/appeal window | Upgrade DB to **Basic ($6/mo)** before 20 Nov, or recreate DB on 1 Nov (expires ~1 Dec) and re-seed. Calendar reminder. |
| 512 MB RAM | WeasyPrint + 2 workers | `WEB_CONCURRENCY=2`, `--max-requests 500`; PDF size caps. |
| No backups on free DB | Data loss risk | Demo data is reproducible by seed; `pg_dump` before submission. |

### 5.4 Rollback
Render dashboard "Rollback" to previous deploy (keeps image); DB migrations designed backward-compatible (add columns nullable first). Git: `git revert` merge commit via PR; never force-push `main`.

## 6. Git workflow

### 6.1 Rules
- `main` protected: require PR, require status checks `lint`, `test`, `security`, `docker` (later `e2e`), require branch up to date, no force-push, no deletion. Reviews not required (solo — GitHub forbids self-approval).
- Branch names: `feat/…`, `fix/…`, `chore/…`, `docs/…`, `test/…`.
- **Conventional Commits** (`feat(finance): lock collections after 7 days`).
- Merge method: **Create a merge commit** only (disable squash & rebase in repo settings) → all feature commits stay in `main` history and every PR is visible as a merge commit.
- PR template (`.github/pull_request_template.md`): Summary · Why · Changes · Screenshots · Tests added · REQ/BR IDs · Checklist (tests pass, migrations included, i18n strings wrapped, audit events added, docs updated, AI-USAGE updated).
- Commit identity: my own name/email; no AI co-author trailers (AI use is declared in AI-USAGE.md instead).
- Never commit secrets; `pre-commit` with ruff + gitleaks.

### 6.2 Day-by-day commit & PR schedule (Plan A)

Every day has ≥ 3 commits. Branch/commit/PR texts below are ready to paste.

| Day | Branch | Commits (in order) | PR title |
|---|---|---|---|
| **Sat 24 Oct** | `main` (initial, before protection) | `chore: initialise repository with MIT licence, README stub and AI-USAGE log` | — |
| | `docs/planning` | `docs(planning): add project plan, requirements and compliance matrix` · `docs(planning): add data model, RBAC matrix and state machines` | **PR #1** docs: project plan and architecture decisions |
| | `chore/project-skeleton` | `chore: scaffold Django 5.2 project with split settings` · `feat(core): add /health endpoint with database check` · `chore(docker): add multi-stage non-root Dockerfile and compose` · `ci: add lint, test, security and docker jobs` · `chore(render): add render.yaml blueprint` | **PR #2** chore: walking skeleton — Django, Docker, CI, Render, /health |
| **Sun 25 Oct** | `feat/auth-rbac-audit` | `feat(accounts): add custom email user model with five roles` · `feat(accounts): add login, logout and lockout with django-axes` · `feat(accounts): add central permission matrix and scoped querysets` · `feat(core): add route registry middleware enforcing default deny` · `feat(audit): add append-only audit log with hash chain` · `test(rbac): add matrix-driven permission tests` | **PR #3** feat: authentication, RBAC matrix and audit foundation |
| **Mon 26 Oct** | `feat/branch-register` | `feat(branches): add cities and branch register with generated codes` · `feat(branches): add branch lifecycle transitions with guards` · `test(branches): cover code generation concurrency and transitions` | **PR #4** feat: branch register with auto codes and lifecycle |
| | `feat/volunteer-applications` | `feat(volunteers): add public application form with validation and spam guards` · `feat(volunteers): add HR review with atomic accept creating members` · `test(volunteers): cover validation, duplicates and accept race` | **PR #5** feat: volunteer applications and HR approval |
| **Tue 27 Oct** | `feat/members` | `feat(volunteers): add teams and volunteer roles` · `feat(volunteers): add member list with search, filters and pagination` · `test(volunteers): cover member search scope and status transitions` | **PR #6** feat: member records with search and filters |
| | `feat/collections` | `feat(finance): add offline collection entry with validation` · `feat(finance): lock collections seven days after entry` · `feat(finance): add void and transfer to main account` · `test(finance): cover lock boundaries with frozen clock` | **PR #7** feat: collections, 7-day lock and transfers |
| **Wed 28 Oct** | `feat/weekly-reports` | `feat(finance): add weekly report auto-drafting and aggregates` · `feat(finance): add submit, return, resubmit and approve transitions` · `feat(finance): snapshot report lines and lock approved reports in DB` · `test(finance): add full report lifecycle test with audit assertions` | **PR #8** feat: weekly report workflow with locking |
| **Thu 29 Oct** | `feat/dashboard-seed` | `feat(seed): add deterministic demo seed and test logins` · `feat(dashboard): add head office KPIs, trends and unsent list` · `test(dashboard): assert expected values from seed` · `feat(seed): add tolerant sample data importer` | **PR #9** feat: head office dashboard and demo seed |
| | `feat/exports` | `feat(exports): add CSV exports with BOM and formula guard` · `feat(exports): add weekly report and monthly summary PDFs` · `test(exports): cover export scope and content` | **PR #10** feat: CSV and PDF exports |
| **Fri 30 Oct** | `feat/public-site-cms` | `feat(cms): add content items with draft, publish and archive` · `feat(public): add seven public pages rendered from CMS` · `feat(public): add sitemap, robots and meta tags` · `test(cms): cover publish states and sanitisation` | **PR #11** feat: public website and content manager |
| **Sat 31 Oct** | `feat/i18n-urdu` | `feat(i18n): add Urdu locale with RTL layout` · `feat(i18n): translate all UI strings to Urdu` · `feat(exports): render Urdu PDFs with Naskh font` · `test(i18n): add translation parity and direction tests` | **PR #12** feat: English/Urdu with right-to-left layout |
| | `test/e2e-lighthouse` | `test(e2e): add smoke journeys with Playwright and axe` · `ci: add Lighthouse CI gate for public pages` · `ci: raise coverage threshold to 70%` | **PR #13** test: E2E smoke tests and Lighthouse gate |
| **Sun 1 Nov** | `chore/security-hardening` | `feat(security): add CSP and strict security headers` · `fix(security): …(findings)` · `perf(public): optimise images and Urdu font subset` | **PR #14** chore: security hardening and performance |
| | `docs/handover` | `docs: add ADRs, API reference and handover guide` · `docs: generate permission table from matrix` · `docs: complete README with test logins and screenshots` | **PR #15** docs: architecture decisions, API docs and handover guide |
| **Twist day** | `feat/<twist-slug>` | 2–4 commits | **PR #16** feat: <twist> |
| **Mon 2 Nov** | `chore/release-1.0.0` | `chore(release): bump version to 1.0.0 and update changelog` · `docs: finalise AI-USAGE log` | **PR #17** chore: release v1.0.0 → tag `v1.0.0` |

Expected: ~55 commits, 17 PRs, 10 distinct days.

### 6.3 Choosing the final commit
1. Merge PR #17 → wait for CI green on `main` → Render deploy finishes → `/health` shows the same short SHA.
2. `git tag -a v1.0.0 -m "ShipLens 1.0 submission"` on that merge commit; `git push origin v1.0.0`; create GitHub Release.
3. Copy `git rev-parse v1.0.0` (full SHA) into the submission form and README "Submitted version".
4. **No pushes to `main` after tagging** until results (hotfixes go on a branch, not merged, unless organisers allow).

### 6.4 Sample PR description (PR #8)
```markdown
## Summary
Weekly report workflow: auto-drafting, submit → return → resubmit → approve → lock.

## Why
Brief: "Weekly reports: drafted automatically, submitted by the Branch Lead, approved or returned by the Finance Reviewer. Approved reports are locked." Gate 2.

## Changes
- `WeeklyReport`, `WeeklyReportLine` models; DB trigger blocks updates once LOCKED
- Transition table in `finance/services/reports.py`
- Lazy `ensure_drafts()`; `generate_weekly_drafts` command
- Snapshot + sha256 hash on submit/resubmit
- Templates for list/detail per state

## Tests
- `test_report_lifecycle_full_audit` (6 audit events in order)
- concurrency: double approve → second gets 409
- locked report raw UPDATE raises

## Traceability
REQ-080…088 · BR-080…090

## Checklist
- [x] Tests pass locally and in CI
- [x] Migrations included
- [x] Strings wrapped for translation
- [x] Audit events for every mutation
- [x] AI-USAGE.md updated
```
