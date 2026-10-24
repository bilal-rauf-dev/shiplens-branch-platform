# 17 — Test Strategy

## 1. Pyramid and tooling
| Level | Share | Tooling | Runs |
|---|---|---|---|
| Unit (pure functions: KPIs, id formats, validators, transition tables, CSV guard) | ~40 % | pytest | every push |
| Service / integration (DB, transactions, triggers, permissions) | ~45 % | pytest-django (Postgres service in CI — **never SQLite**, because triggers/partial indexes/`FOR UPDATE` are Postgres features) | every push |
| HTTP (views via Django test client: status codes, scope, CSRF, headers) | ~12 % | pytest-django `client` | every push |
| E2E smoke | 4–6 tests | Playwright (Chromium) + axe | PR label `e2e` / main |
| Perf/a11y | 5 URLs | Lighthouse CI | main + template PRs |

Helpers: `factory_boy` factories per model; fixtures `seeded_db` (runs `seed_demo`), `clock` (time-machine wrapper over `core.clock`), `login_as(role, branches=…)`.

## 2. Coverage
- Measured on `apps/` (exclude `migrations/`, `settings`, `manage.py`, `wsgi`, `tests`).
- CI gate: `--cov-fail-under=60` from day 1; raise to **70** on 31 Oct once reached. Target ≥ 75 % overall; ≥ 85 % on `services/`, `permissions.py`, `kpis.py`, `audit/`.
- Coverage report attached as CI artifact and summarised in job summary; README badge (static from last main run or Codecov free for public repos — optional).

## 3. Mandatory suites

### 3.1 `T-RBAC-MATRIX` (Gate 3) — generated, cannot drift
- Source of truth: `PERMISSIONS` in code. Frozen expectation: `tests/rbac_expected.yaml` (human-reviewed copy). Test 1: `PERMISSIONS == yaml` (any matrix change must update both in the same PR → visible in review).
- `ROUTE_ACTIONS` maps every url_name → action + HTTP method + fixture factory for an in-scope object.
- Test 2: `@pytest.mark.parametrize("role", ROLES + [ANON])` × `("route", ROUTE_ACTIONS)` → request as role; expected = allowed ? (200/302-success) : (ANON → 302 to login; others → 403). ~70 routes × 6 = ~420 cases, fast with transactional tests.
- Test 3 `T-RBAC-ROUTES`: resolver walk; every pattern registered.
- Test 4 `T-RBAC-SCOPE-*`: for each scoped resource, BL/HR of KHI requesting LHE object → 404; list/export contain zero LHE rows.
- Test 5 `T-RBAC-SERVICE`: services raise `PermissionDenied` for wrong roles.

### 3.2 `T-RPT-LIFECYCLE` (Gate 2)
```text
given seeded KHI week draft (R10), clock = 2026-10-26 10:00 PKT
BL submits           -> status SUBMITTED, revision 1, snapshot total 3,500.00
FR returns "fix"     -> RETURNED
BL resubmits         -> RESUBMITTED, revision 2
FR approves          -> LOCKED, locked_at set
assert audit actions for entity (ordered) ==
  [report.drafted, report.submitted, report.returned, report.resubmitted, report.approved, report.locked]
assert each row has actor/role/request_id, chain verifies
assert raw SQL UPDATE weekly_reports SET status='DRAFT' WHERE id=… raises
assert BL edit of a collection dated in that week -> 409
```
Plus negative tests: BL cannot approve; FR cannot submit; approve with stale revision → 409; return without comment → 400.

### 3.3 `T-DASH-SEED` (Gate 1)
Every value in `09-…` §4.1–4.7 asserted with `Decimal` equality at `as_of=2026-10-31 23:00 PKT`; `T-DASH-REALTIME`; `T-DASH-SAMPLE` when official data arrives.

### 3.4 Other required suites
| ID | Area | Key cases |
|---|---|---|
| `T-COL-LOCK-*` | 7-day lock | created 2026-10-01 10:00 PKT: at 10-08 09:59:59 editable; at 10-08 10:00:00 locked (edit, void → 409); setting=3 → locks 10-04 10:00; UTC/PKT boundary |
| `T-COL-WEEK-CLOSED` | week closure | submitted week blocks create/edit/void; returned week reopens |
| `T-XFER-*` | transfers | totals, mixed-branch rejected, double-send race (two transactions) → one wins |
| `T-ID-*` / `T-MEM-ID-RACE` / `T-BRN-CODE-RACE` | IDs | `TransactionTestCase` + 10 threads → unique, gap-free sequence |
| `T-BRN-TRANSITIONS` | branch SM | every (state, action) pair: allowed vs `InvalidTransition`; close guards |
| `T-APP-*` | applications | each field invalid/valid boundary (name 2/3/100/101 chars, phone formats, age 15/16/17+guardian/100/101, motivation 19/20/1000/1001); honeypot; timing; rate limit 6th → 429; duplicates flagged; no enumeration (identical response bodies); accept atomic (fault injection); accept race |
| `T-MEM-*` | members | search by each field, filter combos, pagination, team-branch constraint, status SM |
| `T-CMS-*` | content | states, live snapshot unaffected by edit, publish guard, slug, sanitiser strips `<script>`/`onerror` |
| `T-I18N-*` | i18n | parity, dir, switcher, Urdu validation messages |
| `T-EXP-*` | exports | see `13-…` §5 |
| `T-AUD-*` | audit | coverage (every POST route), atomic (rollback leaves no audit), immutable (UPDATE/DELETE raise), chain (tamper detect by disabling trigger in test and editing row → verify fails at that id), redaction, security events, export audited |
| `T-SEC-*` | security | CSRF (POST without token → 403 with `enforce_csrf_checks=True`), headers present, cookies flags, lockout after 5, password validators, Argon2 hash prefix, SQLi strings harmless, reflected XSS escaped, mass assignment ignored, error pages generic with DEBUG=False |
| `T-OPS-HEALTH*` | ops | 200 ok, 503 on DB error, no auth required |
| `T-SEED-*` | seed | idempotent; demo users only in DEMO_MODE; 5 role logins work |
| `T-GROWTH-N-BRANCHES` | growth | create 50 branches × 3 collections; KPIs sum correctly; query count on dashboard bounded (assertNumQueries ≤ 25) |
| `T-CONFIG-*` | twist readiness | change `collection_lock_days`, `allow_submit_current_week` → behaviour changes without code edits |
| `T-PUB-*` | public | 7 pages × 2 locales return 200 (`T-PUB-PAGES`), branch visibility by status, no internal data in HTML (`T-PUB-NO-LEAK`: seed member names/amounts absent), meta/hreflang/sitemap (`T-PUB-SEO`) |
| misc | cross-cutting | `T-ASSIGN-CLOSED` (no assignment to closed branch), `T-LOG-NO-PII` (captured logs contain no email/phone from form), `T-COL-NO-ONLINE` (grep: no payment-gateway packages/fields), `T-SM-TABLES` (every transition table entry has permission + audit name), `T-CLOCK-PKT`, `T-AUTH-FORCE-CHANGE`, `T-SEC-COOKIES` |
| `T-DOC-ROUTES` / `T-RBAC-DOC-SYNC` | docs | `docs/api.md` route table and `docs/permissions.md` match generated output |

### 3.5 E2E smoke (Playwright)
| ID | Journey |
|---|---|
| `E2E-01` | Visit 7 public pages in EN and UR; no console errors; axe no serious violations |
| `E2E-02` | Public applies → HR logs in → accepts → member ID shown → member appears in list |
| `E2E-03` | Urdu: `dir=rtl`, switcher round-trip |
| `E2E-04` | BL logs collection → submits report → FR returns → BL resubmits → FR approves → locked badge; audit viewer shows 6 events |
| `E2E-05` | FR dashboard (period Oct 2026) shows K1 `73,250.50` |
| `E2E-LIVE` | Same as 01 + logins, run manually against Render URL on 2 Nov (`BASE_URL` env) |

## 4. Traceability (REQ → BR → Test)

| REQ | BR | Tests |
|---|---|---|
| REQ-020–027 | BR-013 | T-PUB-*, E2E-01 |
| REQ-030–039 | BR-040–055 | T-APP-*, E2E-02 |
| REQ-040–049 | — | T-AUTH-*, T-SEC-LOCKOUT, T-SEC-PASSWORD, T-SEED-DEMO-ONLY |
| REQ-041–045, 142, 147 | — | T-RBAC-MATRIX, T-RBAC-SCOPE-*, T-RBAC-ROUTES, T-RBAC-SERVICE |
| REQ-050–056 | BR-001, 002, 005, 010–014 | T-BRN-*, T-GROWTH-N-BRANCHES |
| REQ-060–065 | BR-003, 055–059 | T-MEM-* |
| REQ-070–077 | BR-060–071 | T-COL-*, T-XFER-* |
| REQ-080–088 | BR-080–090 | T-RPT-*, E2E-04 |
| REQ-090–095 | BR-090, 09 §2 | T-DASH-*, E2E-05 |
| REQ-100–104 | — | T-EXP-*, T-AUD-EXPORT |
| REQ-110–114 | BR-120–123 | T-CMS-*, T-SEC-XSS-CMS |
| REQ-120–125 | BR-130–133 | T-AUD-* |
| REQ-130–134 | — | T-I18N-*, T-EXP-PDF-UR, E2E-03 |
| REQ-140–147 | — | T-SEC-*, CI security job |
| REQ-150–158 | BR-140–141 | CI, T-OPS-*, T-CLOCK-PKT, LHCI |
| REQ-160–161 | — | T-CONFIG-*, T-SM-TABLES |
| REQ-001–011 | — | compliance checks C-xx |

## 5. Every role exercised
SA, FR, CE, BL, HR and ANON each appear in `T-RBAC-MATRIX` for every action; journeys: SA (branches, users, audit), FR (approve/return, dashboard), CE (publish), BL (collections, reports), HR (accept/decline), ANON (form).

## 6. Flakiness controls
Fixed clock in all time-based tests; no real network; Playwright `expect` auto-waits; LHCI 3 runs median; Postgres service health-checked before tests; `pytest -p no:randomly` not used — tests must be order-independent (`pytest-randomly` on).
