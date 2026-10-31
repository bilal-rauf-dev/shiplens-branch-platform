# Security self-review

This review implements planning document 11 and maps the OWASP Top 10 **2021**
labels below. The plan also names the 2025 categories; its exceptional-condition
control is covered by rollback, generic errors and bounded timeouts here.
This is a code/test review, not a penetration-test certification.

## OWASP mapping

| OWASP 2021 | Control and file reference | Automated proof |
|---|---|---|
| A01 Broken Access Control | `apps/accounts/permissions.py`: explicit roles and scoped selectors. `apps/core/routes.py` and `middleware.py`: default deny, login redirects, 404 outside scope. No Django admin or audit-delete/reset HTTP route. | `test_t_rbac_routes`, `test_t_rbac_matrix_route`, scope suites; matrix also asserts SA actions cannot reduce audit rows |
| A02 Cryptographic Failures | `config/settings/prod.py`: HTTPS/proxy handling and DB TLS by default; environment-only signing secret; base/prod Argon2 password hashing; host-only secure cookies. | `test_t_sec_cookies`, `test_t_sec_password_hash`, production hasher/TLS default tests |
| A03 Injection | ORM selectors and forms; `apps/cms/sanitizing.py` allows only fixed HTML tags/attributes/schemes; the CMS template filter sanitizes again before marking safe. `apps/exports/views.py` neutralizes CSV formulas. | `test_t_sec_sqli`, `test_t_sec_xss_reflect`, `test_t_sec_xss_cms`, `test_t_exp_csv_injection`, convention checks |
| A04 Insecure Design | Explicit state-transition services, separate Branch Lead/Finance duties, seven-day collection locks, frozen approved report revisions and transactional audit records. | `test_t_col_lock_before_and_at`, `test_t_app_accept_atomic`, `test_t_app_accept_race`, report acceptance/transition/concurrency suites |
| A05 Security Misconfiguration | `config/settings/base.py`, `prod.py`, `apps/core/middleware.py`: exact CSP, strict referrer/permissions/COOP headers, nosniff, frame denial, HSTS, generic errors; Docker UID 10001. | `test_t_sec_headers`, `test_t_sec_errors`, internal health tests; CI deployment/health/non-root checks |
| A06 Vulnerable and Outdated Components | Exact hashed runtime/dev locks; `.github/workflows/ci.yml` runs pip-audit and the official pinned Gitleaks action; CodeQL and weekly Dependabot. Pip/Docker major upgrades require explicit review. | CI security job; `requirements*.txt`, `.github/dependabot.yml`, `.github/workflows/codeql.yml` |
| A07 Identification and Authentication Failures | `apps/accounts/`: Argon2 first in base/prod, minimum 12 and common/similar/numeric validators, Axes lockout, per-IP login limits, rotated sessions, inactivity/absolute deadlines, immediate session revocation, POST logout, forced temporary-password change. | `test_t_sec_password_hash`, base/prod hasher tests, `test_t_sec_lockout`, `test_t_sec_session_rotate`, login/rate/session tests |
| A08 Software and Data Integrity Failures | Audit hash chain and DB mutation triggers, report snapshot hashes, CI-gated Render deploys, signed application timing token. | `test_t_aud_chain`, `test_t_aud_immutable`, report immutability suites; `render.yaml` uses `autoDeployTrigger: checksPass` |
| A09 Security Logging and Monitoring Failures | Audit security events and exports in the same transaction. `apps/core/logging.py` emits JSON with UUID request correlation, redacts email/phone/credential text, omits request bodies and traceback details. Gunicorn access JSON omits URLs, queries, cookies, client addresses and bodies. | `test_t_aud_security`, `test_t_aud_denied`, `test_t_log_no_pii`, JSON log tests and health correlation test |
| A10 Server-Side Request Forgery | No user-supplied fetch endpoint or uploaded images. CMS image paths are fixed bundled choices; sanitized CMS permits links but no images/iframes. PDF templates use trusted local CSS/fonts and escape narratives; they do not insert user-controlled resource URLs. | CMS sanitizer/choice tests, PDF tests, public no-leak tests; `apps/exports/pdf.py` resolves bundled assets with static finders |

## Specific-control checklist (plan 11 section 2)

| Decision | Implementation / evidence |
|---|---|
| Server sessions, no JWT | DB sessions, `apps/accounts/selectors.py:user_session_keys`; deactivate/reset-password services purge affected sessions. |
| Cookie flags | `prod.py`: `__Host-sid` and `__Host-csrftoken`, Secure, HttpOnly, SameSite=Lax, path `/`, no Domain; tested against emitted cookies, not just constants. |
| CSRF | Django middleware, CSRF tokens in every application POST form; enforced-client tests for login, volunteer application and staff settings. No exemptions. |
| CORS | No app CORS middleware/headers; same-origin forms and resources. Public static assets may use WhiteNoise's public font CORS header. |
| Rate limiting | Axes; DB-backed login minute/day mutex; signed form timing/honeypot and hourly/daily IP limits; export user limits. Health is intentionally unlimited. |
| Validation / output encoding | Explicit form fields, autoescape, one re-sanitizing CMS safe boundary, CSV text formula guard. |
| Mass assignment | Codes/status/actors/branch scope are set by services; unexpected payload fields are ignored. Existing mass-assignment tests exercise member/report edits. |
| IDOR | Scoped lookup before retrieval; out-of-scope IDs return 404. No unrestricted direct model `.get()` or `.save()` in view modules. |
| Secrets | Env-only signing/DB/demo secrets, `.env` excluded from Git/image, Gitleaks CI; Render generates the signing key. |
| Demo credentials | Demo-only seed, protected demo accounts, operator-only shell rebuild. No HTTP reset view, permission, button or URL exists. |
| Public form spam | Signed elapsed-time token, honeypot, field bounds, request limits, no uploads/outbound email. |
| Applicant PII | Scoped HR/SA access, no PII in finance exports or public pages, hashed applicant IP; retention/purge is a documented optional feature, not an implemented scheduler. |
| Errors | DEBUG false in prod, localized generic 400/403/404/500 pages; logs retain exception type and request ID, not exception details. |
| Uploads | None; bundled illustration choices only. |
| Backups | Operator responsibility. Free-tier DB has no automatic backups; take a restricted-access dump before judging and any deliberate rebuild. |
| CSP | `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'; object-src 'none'`. No unsafe-inline, unsafe-eval, nonce or report-only policy. |

CSP directive order is semantically irrelevant and django-csp 4 serializes it in
arbitrary order; tests compare the exact directive/source set, allowing no extras.
CSP/header middleware wraps the exact `/health` shortcut. That shortcut still
bypasses SSL redirects and host validation for internal IP/HTTP probes; all other
routes retain those checks. Request-ID middleware wraps the shortcut too.
HSTS preload remains disabled because this app does not own `onrender.com`.
Referrer policy is `strict-origin-when-cross-origin`, as requested by P13.

## STRIDE-lite threat model

| Threat | Asset | Mitigation / boundary |
|---|---|---|
| Spoofing: credential stuffing | Staff identities | Argon2, generic login errors, Axes and per-IP limits, session rotation/deadlines. |
| Tampering: Branch Lead changes past figures | Collections/reports | Seven-day lock, closed-week rule, immutable approved snapshots and audit in transaction. |
| Tampering/elevation: Finance fabricates its own receipts | Financial totals | Finance cannot create/edit collections; approval role is separate. |
| Repudiation: insider removes evidence | Audit history | Append-only DB triggers, canonical hash chain, no HTTP mutation/rebuild route. |
| Denial of service: bot application flood | DB and HR time | Honeypot, signed timing and request/length limits; no uploads or email fan-out. |
| Information disclosure: XSS / applicant enumeration | Sessions and PII | Escape output, sanitize CMS, CSP, scoped selectors, generic errors and 404s. |
| Elevation: changed branch ID | Members/applications/finance | Permission checks at routes and services plus scoped object lookup. |
| Tampering: public demo vandalism | Fictional demo data | No hard deletes, demo-account protections, operator rebuild from authored history. |

## Documented exceptions: every application raw-SQL use

These statements do not interpolate request data. Ordinary reads/writes use the
ORM. Migration SQL is fixed deployment code; runtime exceptions are narrowly scoped.

| File | SQL and why it is safe |
|---|---|
| `apps/audit/migrations/0002_immutable_audit.py` | Fixed PL/pgSQL function and triggers reject audit UPDATE, DELETE and TRUNCATE. |
| `apps/branches/migrations/0004_complete_register.py` | Fixed immutable branch-code trigger. |
| `apps/volunteers/migrations/0003_member_integrity.py` | Fixed member-integrity trigger, preventing invalid cross-branch links. |
| `apps/finance/migrations/0002_transfer_guards.py` | Fixed collection/transfer integrity and immutability triggers. |
| `apps/finance/migrations/0004_report_immutability.py` | Fixed report/revision/line immutability triggers. |
| `apps/audit/services.py:_lock_chain` | Parameterized fixed advisory lock serializes hash-chain writes; called within the business transaction. |
| `apps/audit/services.py:record` | Parameterized `nextval(pg_get_serial_sequence(...))` reserves the ID before canonical hashing. Table/column names are fixed constants. |
| `apps/seed/services.py:_reset_tables` | Operator-only demo rebuild: fixed table allowlist, DEMO_MODE/password guard, trigger DDL and TRUNCATE plus re-import in one transaction. Failed imports restore rows, sequences and guards. Never reachable over HTTP. |
| `apps/core/selectors.py:check_database` | Literal `SELECT 1` on a separate connection; 2-second connect/query limits, closed in finally, generic result only. |

Tests also execute deliberate mutation SQL to prove trigger rejection, `SHOW`
to check the timeout, and guarded cleanup SQL in `tests/conftest.py`. These
are test-only operations and are not imported by application entry points.
Ordinary statements have a 15-second timeout; Gunicorn requests have a 60-second
limit. The health connection overrides the statement timeout to two seconds.

## Findings closed in P13

- CSP was pinned but not enabled; base now enforces the exact planned allowlist.
- Browser permission/referrer/COOP headers now cover health and error responses.
- Plain stdout logs became redacted JSON with request IDs; Gunicorn access records
  no longer expose request URLs/query strings. Correlation also covers health.
- The normal DB statement timeout was missing; it is now 15 seconds.
- Production DB TLS was implicit in deployment URLs; it now defaults to required.
  The isolated disposable Compose smoke DB explicitly opts out, because its local
  PostgreSQL container has no TLS listener. Dev/test stay local as before.
- CSRF failures now use the same generic localized 403 page, without framework
  diagnostics or inline styles.
- Convention checks now cover `report_views.py`/`pdf_views.py` and aliased
  `mark_safe` imports, in addition to existing CSRF/safe-filter protections.
- Gitleaks was already present; no duplicate workflow/action was added.

## Known limitations and operator checks

The DB owner can disable triggers and rewrite history. A retained external chain
tip is needed to detect truncation of the whole tail after bypassing guards.
The free-tier database has no automatic backups. Demo passwords are shared with
judges and the data is fictional; demo mode must not contain real operational PII.
TLS `require` encrypts but does not validate a CA/hostname; deployments needing that
must provide `sslmode=verify-full` and their CA configuration in the DB URL/options.

Authorized staff GET filters can contain search terms (including an email) in the
browser URL/history. Routes themselves contain only codes/IDs; operational access
logs omit URL/query data. Private pages use no-store and cross-origin referrers
send only the origin. Changing filter semantics would require a separate UX/API
change. Restricted audit rows intentionally contain captured actor identity;
these are distinct from operational stdout logs.

Render/GitHub deployment protections and backups are operator-managed settings.
The repository configures checks-pass deploys, HTTPS/proxy handling and a non-root
image, but cannot certify settings outside the repository. Keep a deployment
review and backup/restore checklist alongside the handover instructions.

## Browser verification

`tests/security/test_browser.py` runs Chromium against a local production image.
Set `BROWSER_URL`, `BROWSER_EMAIL`, `BROWSER_PASSWORD` for that disposable dataset
and run the file directly, or select it with `pytest -m visual`.
The local HTTP harness supplies the trusted HTTPS proxy header and trusts only its
loopback Origin; real deployments use Render TLS. Production cookie flags remain
unchanged and are tested separately with an enforced-CSRF HTTPS client.
P13 Step 1 verified both EN/UR dashboards (two charts), CMS editor and PDF download
with zero console errors or CSP violation events.
