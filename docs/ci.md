# Continuous integration

`ci.yml` runs on pull requests and pushes to `main`. Its four job names match
the required checks in planning document 15, section 4.1.

| Job | What it checks | Plan mapping |
| --- | --- | --- |
| `lint` | Ruff lint and formatting, logical CSS properties, no CSRF exemptions or direct model writes/lookups in views | Explainability and thin-view rules in AGENTS.md; plan 15 §4.1 |
| `test` | PostgreSQL 16, production deployment settings, missing migrations, Django translation configuration, pytest and at least 90% coverage | Plan 17's PostgreSQL-only strategy and audit coverage gate |
| `security` | `pip-audit` against the runtime lock and Gitleaks against repository history | Plan 11's security controls and plan 15 §4.1 |
| `docker` | Build with the commit SHA; start the production image and PostgreSQL; wait for Docker health; GET `/health`; require UID 10001 | Plan 15 §§1–2 and §4.1 |

Coverage XML is uploaded and its total is written to the GitHub job summary,
including when tests fail after producing a report. The coverage threshold is
90%. The original P1 gate was 60%; the audit fixes raised it to 90%.

All action references use full commit SHAs with release comments. Workflow
permissions default to `contents: read`; only the CodeQL job gets the additional
permissions needed to upload security analysis. Gitleaks PR comments are disabled.
Superseded runs are cancelled using workflow/ref concurrency groups.

`codeql.yml` analyzes Python on pull requests, pushes to `main`, and weekly.
Dependabot checks pip dependencies, GitHub Actions and Docker images weekly.
Pip and Docker semver-major updates are ignored; stack upgrades need explicit review.
CI compiles the Urdu catalogue, checks fresh message extraction and runs parity
and rendered-usage tests. GNU gettext is installed for those checks.

## Local verification

With the Python dependencies installed and the environment variables configured:

```text
ruff check .
ruff format --check .
python bin/check_conventions.py
python manage.py check --deploy --fail-level WARNING --settings=config.settings.prod
python manage.py makemigrations --check --dry-run
python manage.py check --tag translation
pytest --cov=apps --cov-report=xml --cov-report=term-missing --cov-fail-under=90
pip-audit -r requirements.txt
```

`docker-compose.ci.yml` is a disposable production stack without a source bind mount or
`.env` file. Use a separate Compose project name when testing it locally, and set
`CI_WEB_PORT` to a free port if development already occupies port 8000. Its database
is disposable; the workflow removes its containers and volumes on completion.

`pip-audit` is pinned in the development lock and is not installed in the production
image. Django's existing `security.W021` waiver is retained because HSTS preloading
is deliberately disabled on the shared Render domain.

## Permission regression checks

`tests/rbac/registry.py` describes each protected route's HTTP method, URL builder,
fixture factory and expected success status. The fixture supplies valid form data
and an in-scope target when the route needs one. The shared scenario assigns a
branch to Branch Lead and HR Lead actors; current dashboard/list placeholders do
not need a domain object of their own.

When adding a route to `ROUTE_ACTIONS`, add its request recipe in the same change.
The coverage test rejects missing and obsolete recipes. The matrix suite iterates
`ROUTE_ACTIONS` directly for all five roles and ANON. It derives access from
`PERMISSIONS`, checks allowed success statuses, redirects anonymous users to login
with the original URL in `next`, and requires 403 for other roles. Denials must not
alter domain records. Allowed POSTs must use valid data and append an audit event.

`T-RBAC-SERVICE` also invokes administration services directly for every disallowed
role and ANON, requiring `PermissionDenied` and unchanged domain records. An
additional check covers anonymous access to the own-password service. These tests
run in the existing PostgreSQL pytest job with the current dependencies.

For a focused run, use `pytest tests/rbac`. The frozen permission table, generated
documentation sync, URL resolver coverage and object-scope tests remain separate
checks so they can catch different classes of mistake.

The member register performance check runs in the normal PostgreSQL pytest job.
Find it with `pytest -m performance tests/volunteers/test_member_search.py`. It
creates 5,000 members with `bulk_create`, then checks the rendered filtered view
uses at most 8 queries and takes less than 300ms after template warm-up. Data setup
and authentication middleware are outside the measurement. Query count and
elapsed milliseconds are exposed as pytest `record_property` values for reports.

Enabling `django.contrib.postgres` also installs connection type handlers. The
isolated health-probe connection uses Django's `NO_DB_ALIAS` to skip that handler
setup for its `SELECT 1`; it still copies the configured database name and keeps
its connection/query timeouts. Real PostgreSQL health tests cover this integration.


Ordinary tests use MD5 hashing only in `config.settings.test` to reduce runtime.
Base and production settings retain Argon2 first. Dedicated password-hash and
user-creation security tests explicitly select the production hashers and still
check real Argon2 hashes; settings tests guard the base/production defaults.
