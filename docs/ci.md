# Continuous integration

`ci.yml` runs on pull requests and pushes to `main`. Its four job names match
the required checks in planning document 15, section 4.1.

| Job | What it checks | Plan mapping |
| --- | --- | --- |
| `lint` | Ruff lint and formatting, logical CSS properties, no CSRF exemptions or direct model writes/lookups in views | Explainability and thin-view rules in AGENTS.md; plan 15 §4.1 |
| `test` | PostgreSQL 16, production deployment settings, missing migrations, Django translation configuration, pytest and at least 60% coverage | Plan 17's PostgreSQL-only test strategy and initial coverage gate |
| `security` | `pip-audit` against the runtime lock and Gitleaks against repository history | Plan 11's security controls and plan 15 §4.1 |
| `docker` | Build with the commit SHA; start the production image and PostgreSQL; wait for Docker health; GET `/health`; require UID 10001 | Plan 15 §§1–2 and §4.1 |

Coverage XML is uploaded and its total is written to the GitHub job summary,
including when tests fail after producing a report. The coverage threshold is
60% for P1; the planned later increase to 70% remains a separate change.

All action references use full commit SHAs with release comments. Workflow
permissions default to `contents: read`; only the CodeQL job gets the additional
permissions needed to upload security analysis. Gitleaks PR comments are disabled.
Superseded runs are cancelled using workflow/ref concurrency groups.

`codeql.yml` analyzes Python on pull requests, pushes to `main`, and weekly.
Dependabot checks pip dependencies, GitHub Actions and Docker images weekly.
E2E and Lighthouse jobs are outside P1. Full Urdu catalogue parity checks belong
to the later translation pass; P1 checks Django's translation configuration.

## Local verification

With the Python dependencies installed and the environment variables configured:

```text
ruff check .
ruff format --check .
python bin/check_conventions.py
python manage.py check --deploy --fail-level WARNING --settings=config.settings.prod
python manage.py makemigrations --check --dry-run
python manage.py check --tag translation
pytest --cov=apps --cov-report=xml --cov-report=term-missing --cov-fail-under=60
pip-audit -r requirements.txt
```

`compose.ci.yml` is a disposable production stack without a source bind mount or
`.env` file. Use a separate Compose project name when testing it locally, and set
`CI_WEB_PORT` to a free port if development already occupies port 8000. Its database
is disposable; the workflow removes its containers and volumes on completion.

`pip-audit` is pinned in the development lock and is not installed in the production
image. Django's existing `security.W021` waiver is retained because HSTS preloading
is deliberately disabled on the shared Render domain.
