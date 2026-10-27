# ShipLens — Branch-to-Head-Office Management Platform

A bilingual (English/Urdu) platform that connects volunteer branches to head office: a public website with volunteer applications, plus a secure back office for branches, members, offline collections, weekly reports with approval, a head-office dashboard and a full audit trail.

Solo entry for **ShipLens 1.0** by EchoLens Digital. Work in progress; the full README comes with the release.

The current build includes English and Urdu home pages, secure email login and
password changes, role-specific placeholder pages, a database health endpoint,
Docker packaging and CI. The central permission matrix and branch assignments are
implemented, with default-deny route enforcement, localized error pages and an
append-only audit log. The branch and city register provides scoped lists,
audited editing and lifecycle controls. Other domain screens and demo seed data
arrive in later tasks. The public volunteer form validates submissions, limits
spam and stores applicant details for the upcoming HR review workflow.

- Planning documents: [`docs/planning/`](docs/planning/00-executive-summary.md)
- AI usage declaration: [`AI-USAGE.md`](AI-USAGE.md)
- Licence: [MIT](LICENSE)
- CI jobs and checks: [`docs/ci.md`](docs/ci.md)
- Generated permission matrix and scope rules: [`docs/permissions.md`](docs/permissions.md)
- Branch model, counters and migration notes: [`docs/branch-register.md`](docs/branch-register.md)
- Public volunteer form and privacy controls: [`docs/volunteer-applications.md`](docs/volunteer-applications.md)

## Run locally

Install Docker with Compose support (Docker Desktop on Windows). A host Python
installation is not required to run the application.

For a fresh checkout, copy the example environment file. Keep an existing `.env`:

```sh
cp .env.example .env
```

Edit `.env` and replace the `SECRET_KEY` placeholder with a long random signing key.
You can generate one without installing Python locally:

```sh
docker run --rm python:3.12-slim-bookworm python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The example's PostgreSQL credentials are for local development. Keep the
`DATABASE_URL` hostname as `db` inside Compose; if you change the database name,
user or password, update both `DATABASE_URL` and the corresponding `POSTGRES_*`
values. `.env` is ignored by Git and excluded from Docker builds.

Start the stack:

```sh
docker compose up --build
```

Compose waits for PostgreSQL, applies migrations, creates the database cache table,
compiles translation catalogs, then starts Django's development server. Open:

- [English home](http://localhost:8000/en/)
- [Urdu home](http://localhost:8000/ur/)
- [Health endpoint](http://localhost:8000/health), which returns HTTP 200 with
  `status` and `db` both `ok` when PostgreSQL is reachable.

To stop the stack, run `docker compose down` in another terminal. The named database
volume is retained. See [CI documentation](docs/ci.md) for checks and the PostgreSQL
test requirements.

To bootstrap a local staff account after updating an existing checkout, apply the
migrations and run Django's interactive account-creation command:

```sh
docker compose exec web python manage.py migrate --noinput
docker compose exec web python manage.py createsuperuser
```

This creates our `SUPER_ADMIN` role; the application does not use Django's admin,
`is_staff`, or `is_superuser` permission flags. Open
[staff login](http://localhost:8000/en/accounts/login/). Passwords require at least
12 characters and must pass common-password, similarity and numeric-password
checks. Five failed attempts lock that email/client-IP pair for 15 minutes.
Sessions expire after one hour idle or eight hours from login; activity does not
extend the absolute deadline.

The permission source is `apps/accounts/permissions.py`. After an intentional
matrix change, regenerate its documentation with:

```sh
docker compose exec web python manage.py export_permissions
```

The tests compare the matrix to the frozen plan copy in `tests/rbac_expected.yaml`
and verify that the generated document matches the committed file. That YAML file
uses JSON syntax (a YAML 1.2 subset), so the tests need no extra YAML dependency.
`tests/rbac/registry.py` supplies a valid request recipe for every protected route.
The suite checks every role and anonymous access against the central matrix, plus
direct service denials. New protected routes must add a recipe or CI fails; see
[permission regression checks](docs/ci.md#permission-regression-checks).
Super Admins can open [Users](http://localhost:8000/en/app/users/) and
[System settings](http://localhost:8000/en/app/settings/) from the navigation.
User creation and password reset show a generated temporary password only in that
response, with caching disabled. Copy it before leaving; the next login requires a
password change. Deactivation and reset revoke existing sessions.

The last active Super Admin cannot be demoted or deactivated, including competing
requests. Demo accounts cannot be edited or reset; demo Super Admins cannot create
or promote another Super Admin. Only Branch Leads and HR Leads may receive branch
assignments, and new assignments cannot target closed branches. Removing a branch
assignment removes only the access link and records its history in the audit log.
Changing a lead to a role without branch scope removes their assignment links.

Settings override deployment defaults immediately: collection lock days (1–30),
current-week submission, minimum volunteer age (14–25), and applications per hour
(1–50). `apply_rate_per_hour` is the numeric application-rate rule; the former
`apply_rate` string default is replaced. Every administration write uses an atomic
service and records an audit event. All user mutation services set `updated_at`
from `clock.now()`.

Every named route must appear in `apps/core/routes.py`, either in `PUBLIC_ROUTES`
or mapped to a permission in `ROUTE_ACTIONS`. Unregistered routes return 404;
private routes redirect anonymous visitors to login and return 403 for roles
without the declared permission. Generic list/detail views use
`PermissionRequiredMixin` to filter their querysets before object lookup. Public
login continues to redirect already signed-in visitors to their role's home.

The 403, 404 and 500 pages use generic text with English/Urdu translations. Error
rendering avoids request context processors and database lookups. Translation
catalogs compile during Docker builds and Compose startup. Compose selects the
`dev` stage, which adds GNU gettext for source-mounted development. The default
build ends at `production` (based on the lean `runtime` stage); CI and Render keep
building without a target and do not include gettext or `msgfmt`.
The entrypoint disables Gunicorn's optional control socket because the runtime
user has no home directory; container lifecycle commands manage the server.

Audit rows record authentication events, password changes, branch assignments and
permission denials (at most one per user/route every 60 seconds). Request context
captures the validated client IP, a truncated user agent and the UUID request ID.
Only the attempted email is captured from failed-login credentials. Secret keys
are redacted recursively from before/after/metadata, and before/after retain only
changed fields. See [audit design](docs/audit.md) for the hash and database guards.
Verify the stored chain with:

```sh
docker compose exec web python manage.py verify_audit_chain
```

## Deploy

The root [`render.yaml`](render.yaml) defines a Docker web service and a PostgreSQL
16 database on the free plan in Singapore, following planning document 15 §5.1.
Render builds the existing Dockerfile and checks `/health`.

1. Commit and push the finished changes to your GitHub repository's `main` branch,
   then confirm that CI passes.
2. In the [Render Dashboard](https://dashboard.render.com/), choose **New → Blueprint**,
   connect the GitHub repository, select `main`, and use the root `render.yaml`.
3. Review the `shiplens-web` and `shiplens-db` resources. Enter `DEMO_PASSWORD` when
   prompted; keep it in Render's environment settings and out of the repository.
4. Create the Blueprint and wait for the web service to become healthy. The
   production entrypoint runs migrations and creates the cache table before
   starting gunicorn. It runs `seed_demo --if-empty` only when demo mode is enabled
   and that command exists; seeding is skipped until that command is implemented.
5. Open the actual HTTPS service URL shown by Render and check `/health`, `/en/`
   and `/ur/`. Health reports the first seven characters of `RENDER_GIT_COMMIT`.
6. Confirm auto-deploy is **After CI Checks Pass**. Subsequent `main` commits deploy
   after their CI checks pass, as configured by `autoDeployTrigger: checksPass`.

Render supplies `RENDER_EXTERNAL_HOSTNAME`. Settings automatically append that
hostname to `ALLOWED_HOSTS` and its HTTPS origin to `CSRF_TRUSTED_ORIGINS`, so an
assigned hostname that differs from `shiplens-web.onrender.com` still works. Add any
custom domain explicitly to the two environment variables below. Blueprint field
and secret behavior is described in the [Render Blueprint reference](https://render.com/docs/blueprint-spec).

### Environment variables

| Variable | Local / Render configuration |
| --- | --- |
| `SECRET_KEY` | Set a random value locally; Render generates the secret with `generateValue: true`. |
| `DATABASE_URL` | Local example connects to Compose's `db`; Render injects the linked database's private connection string. |
| `DJANGO_SETTINGS_MODULE` | Compose selects `config.settings.dev`; the Blueprint selects `config.settings.prod`. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames, without schemes or ports. Blueprint default: `shiplens-web.onrender.com`. Add custom domains here. |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated origins including their scheme. Blueprint default: `https://shiplens-web.onrender.com`. Add custom HTTPS origins here. |
| `RENDER_EXTERNAL_HOSTNAME` | Supplied automatically by Render and appended to the host/origin settings. Leave empty locally. |
| `TRUSTED_PROXY_HOPS` | Trusted forwarded entries counted from the right; default `1` for Render. Set `0` to ignore forwarding headers when running without a trusted reverse proxy. The same client-IP helper is used for login lockout and rate-limit keys. |
| `DEMO_MODE` | `false` in the local example; `true` in the Blueprint. Enables guarded demo seeding once the command exists. |
| `DEMO_PASSWORD` | Set manually during Blueprint creation (`sync: false`). Used when demo accounts are implemented. Manage later changes in Render's environment settings. |
| `WEB_CONCURRENCY` | Production gunicorn worker count; Blueprint value: `2`. |
| `LOG_LEVEL` | Python logging level; Blueprint value: `INFO`. |
| `PORT` | Render supplies the listening port. Local default: `8000`; gunicorn and the Docker healthcheck use this value. |
| `RENDER_GIT_COMMIT` | Supplied by Render; used for the short health-response version. |
| `GIT_SHA` | Image build argument / fallback version when Render's commit variable is absent. Defaults to `dev`. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Local Compose database settings only; Render manages its linked database credentials. |

The free web service sleeps after inactivity, so the first request can take about
a minute. Free PostgreSQL expires 30 days after creation and has no backups; plan
an upgrade or a replacement database before expiry if the judging window extends
beyond it. See [Render's free-instance limits](https://render.com/docs/free).
