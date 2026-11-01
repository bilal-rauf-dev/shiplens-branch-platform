# Handover and operations

ShipLens serves public visitors and five staff roles for a volunteer organisation.
The public demo is fictional Ujala Volunteer Network. Branch Leads record offline
money and weekly reports; Finance reviews; HR manages applications/members;
Content Editors publish; Super Admin administers and inspects audit history.
The [architecture](architecture.md), [route reference](api.md) and
[permission matrix](permissions.md) describe the implementation.

This guide documents operator procedures. It does not confirm the live deployment,
GitHub checks, backup state or final judged commit. Keep the submitted repository,
demo, credentials and video available for the organiser's required judging window.

## Environments and deployment

Local development uses `docker-compose.yml`, `config.settings.dev`, a source mount
and a persistent PostgreSQL volume. [Local setup and environment values](../README.md#-run-locally)
are in the README. Tests create a separate PostgreSQL test database. Browser write
journeys require the disposable production overlay in [testing](testing.md).
Render uses `config.settings.prod`, Docker/Gunicorn and a managed PostgreSQL 16 DB.
Never reuse a live database for tests or browser write journeys.

Deploy through the root `render.yaml` Blueprint: connect the repository and `main`,
review Singapore/free-plan resources, supply `DEMO_PASSWORD` and deploy after CI.
Render supplies the database URL, external hostname and commit environment values;
it generates the signing key. `bin/start.sh` calls `manage.py startup` in one Python
process: migrations → cache table → demo `--if-empty` when enabled → missing
weekly drafts in every mode, then Gunicorn. A seeded
marker preserves demo changes on ordinary redeployments. Development Compose does
not call startup's seeding path.

After a deploy, check `/health` for HTTP 200, `db=ok` and the expected seven-character
commit version; check HTTP→HTTPS redirect, certificate, `/en/`, `/ur/`, five logins
and the October dashboard. Check actual GitHub job results and Render's checks-pass
setting, not only the configuration file. A successful internal HTTP health probe
does not prove public TLS. Use [CI](ci.md) and [testing](testing.md) for those checks.

For rollback, select a compatible prior image in Render only after reviewing schema
compatibility. An image rollback does not reverse migrations or restore data. Test
recovery against a separate database first. The owner handles publishing and Git
release operations; repository agents follow AGENTS.md's restricted Git commands.

## Rebuild the live fictional demo

`seed_demo --reset` deliberately replaces demo domain data, settings overrides,
audit history and sessions. It restores authored history and sets every demo
password. It is allowed only with `DEMO_MODE=true` and a password of at least twelve
characters. It has no HTTP endpoint or Super Admin button. Never use it to preserve
real operational data. [Audit](audit.md) explains its transactional SQL boundary.

Before recording or judging, agree the maintenance window, verify the target DB
and save any changes/audit evidence that must survive. Stop demo writes while
rebuilding. Free web hosting has no required operator shell, so run the command
from an operator machine against the live database's **external** TLS URL. Use the
same source revision as the deployed app. The commands below use a POSIX shell
(for example WSL on Windows), Docker, and hidden prompts; no secrets belong in Git.

```sh
docker build --tag shiplens:operator .
read -r -s -p 'Live external PostgreSQL URL (TLS): ' DATABASE_URL; printf '\n'
read -r -s -p 'Deployment signing key: ' SECRET_KEY; printf '\n'
read -r -s -p 'Demo password: ' DEMO_PASSWORD; printf '\n'
export DATABASE_URL SECRET_KEY DEMO_PASSWORD
docker run --rm --env DATABASE_URL --env SECRET_KEY --env DEMO_PASSWORD \
  --env DEMO_MODE=true --env DJANGO_SETTINGS_MODULE=config.settings.prod \
  shiplens:operator python manage.py seed_demo --reset
unset DATABASE_URL SECRET_KEY DEMO_PASSWORD
```

Use the Render database Info page's external URL, with TLS enabled, not the private
hostname used by the web service. Limit external database access to the operator's
IP where practical; remove temporary access afterward. See
[Render connection guidance](https://render.com/docs/postgresql-creating-connecting).
Confirm the command succeeded, audit verification passes, all five logins work,
R9 is Submitted, R10 is Draft, and the October reference values match the README.
Reports are found by branch/week, not their short sample labels or numeric IDs.

For a local demo, load the desired environment into Compose and run
`docker compose exec web python manage.py seed_demo --reset`. Recreate the web
container after editing `.env`; `exec` inherits the running container's environment.

## Rotate secrets and DEMO_PASSWORD

Changing `DEMO_PASSWORD` in Render and redeploying does not rehash existing accounts:
startup skips a marked seed. To rotate a fictional demo's shared password:

1. Back up or retain any needed demonstration changes; announce the rebuild window.
2. Set a new strong `DEMO_PASSWORD` in Render and redeploy. Keep it out of logs/video.
3. Run the operator rebuild above using the same new password and live external URL.
4. Test all five logins, replace the password in the submission form/owner's private
   notes, and verify earlier sessions are logged out. The rebuild clears sessions.

There is no implemented password-only demo rotation command. If changes/history
must be preserved, plan a separately reviewed audited rotation service instead of
using reset. Ordinary non-demo password resets use Users and revoke that user's
sessions. Changing `DEMO_MODE` does not delete existing demo accounts.

Rotate `SECRET_KEY` through deployment environment configuration and redeploy;
signed data/sessions may become invalid. Preserve the current key securely before
maintenance and test logins afterward. Rotate DB credentials through the database
provider, update `DATABASE_URL`/Blueprint binding, deploy and check health. Revoke
old credentials after the new connection works. Consult [security](security.md)
for TLS, cookie and audit-owner limitations.

## Back up and restore with PostgreSQL tools

Use PostgreSQL 16 client tools and the Render **external** host. Configure the
following in an operator shell using values from the database Info page:

```sh
export PGHOST='external-host-from-render'
export PGPORT=5432
export PGDATABASE='database-name'
export PGUSER='database-user'
export PGSSLMODE=require
read -r -s -p 'Database password: ' PGPASSWORD; printf '\n'
export PGPASSWORD
umask 077
BACKUP_FILE="/secure/backup-folder/shiplens-$(date +%Y%m%dT%H%M%S).dump"
pg_dump --format=custom --no-owner --no-privileges --file="$BACKUP_FILE"
pg_restore --list "$BACKUP_FILE"
unset PGPASSWORD
```

Replace the example backup directory with an existing restricted directory outside
the repository. Retain dumps in protected storage, with their source DB, timestamp
and deployed revision recorded separately. A readable archive listing is only an
initial check. Test a full restore to an isolated empty PostgreSQL 16 database;
point the PG variables at that target, set its password, and run:

```sh
pg_restore --no-owner --no-privileges --exit-on-error --single-transaction "$BACKUP_FILE"
```

Restore into an empty database before application startup creates tables. Do not
use `--clean` against the working demo. Use a matching application revision, verify
`verify_audit_chain`, reference totals and logins, then switch the web service's
database URL only after verification. Do not test a restore on the source database.
The [Render backup guide](https://render.com/docs/postgresql-backups) documents
logical backups and paid recovery options. The free compute plan has no managed
backups; a checked dump is the operator's responsibility.

## Replace an expiring free Render database

Render's current [free-plan limits](https://render.com/docs/free) state a 30-day
database lifetime and one active free database per workspace. Check the database's
actual expiry date in the dashboard; do not calculate it from repository dates.
Upgrading avoids a destructive replacement and downtime.

If staying on free, finish this **before expiry**, while the source is accessible:

1. Take a custom dump and prove it restores to a separate local database. Retain the
   current connection/deployment settings and any independent audit-chain evidence.
2. Schedule downtime and stop application writes. A second free database cannot
   coexist in that workspace: delete the old one only after the backup/recovery
   check and the owner's deliberate decision to replace it. This deletion is permanent.
3. Create a new PostgreSQL **16** database in **Singapore**, using the intended name.
   Update the web service's `DATABASE_URL` to its new internal URL and correct any
   stale `fromDatabase` binding in the Blueprint if the name changed.
4. To preserve changes, restore the verified archive into the empty DB before
   starting the app. For a deliberate fresh fictional demo, leave it empty and let
   startup migrate and seed with `--if-empty` using the configured demo password.
5. Deploy and verify health/version, logins, audit chain, reports and reference
   totals. Record the new expiry date and arrange the next operator check. Updating
   a connection string alone does not copy records.

No scheduled backup, database replacement or expiry reminder is implemented by
the application. Provision and rehearse recovery ahead of the judging window.

## Routine administration and changes

Use a non-demo Super Admin for real administrative setup; demo identities are
protected. For a fresh non-demo database, bootstrap with `createsuperuser` from
the operator environment. Normal staff administration then uses audited services.

| Need | Procedure |
| --- | --- |
| Add a city | Cities → Create; unique three-letter uppercase code and English/Urdu names. Codes remain fixed. |
| Add a branch | Branches → Create; choose city and bilingual details. The service generates a code and Forming status. Activate it to allow collections and drafts. |
| Add a user | Users → Create; choose one role. Copy the temporary password from its one-time response. The user must change it on first login. |
| Assign a lead | User detail → branch assignment. Only Branch/HR Leads can be assigned; the destination must not be Closed. |
| Change business rules | System settings → collection lock days, current-week submission, minimum age or application hourly limit. The service validates and audits overrides. Week start is fixed Monday. |
| Add a role/permission | Update Role plus DB checks/migrations, PERMISSIONS and the reviewed frozen tests/rbac_expected.yaml; update scope, landing/navigation and test recipes. Register routes, regenerate permissions/routes and run the full checks. |
| Add a report field | Extend finance/report_fields.py REPORT_FIELDS, wrap its label for translation, add Urdu text and boundary tests. The form, service validation and JSON snapshot use the registry; ordinary new narrative fields need no schema change. |
| Add a language | Extend LANGUAGES, catalogs, fonts/formats and bidi checks. Also update fixed en/ur model/form/CMS choices and database checks where needed; adding only a catalog is insufficient. See the Urdu guide. |

From the source-mounted local development checkout, regenerate references with
`manage.py export_permissions`, `manage.py export_routes` and
`python bin/export_model_diagram.py` in its configured Python environment.
The production image intentionally excludes docs/tests, so do not expect it to
write the documentation pack. See [Urdu workflow](i18n-glossary.md) and
[test requirements](ci.md) instead of duplicating those guides here.

`generate_weekly_drafts` creates missing drafts for currently Active branches
and prints the number of new reports. Production startup always runs it after
seeding, including outside demo mode. The Branch Lead Reports list calls the same
service for a process that stays running across Monday; dashboards do not create
drafts. Once drafted, L2 shows the current week's report as latest, rather than
planning/09's older R10 example. K8/K9 and money are unchanged by Draft rows. A successful close needs no unsent receipts or open reports; read the
[implemented rules](business-rules.md) before changing workflow behavior.

## Monitoring and incidents

Check public HTTPS `/health`, Render deployment/runtime logs and GitHub checks.
Health returns 503 on DB failure with no exception detail. Operational logs use
request UUIDs; staff audit history is a separate restricted record. Super Admin
can filter Audit log and run Verify chain, or an operator can run
`python manage.py verify_audit_chain`. Retain an independent chain tip with backup
evidence when tamper detection across privileged changes matters.

For an incident: record the time, deployed version, request ID and symptom;
restrict affected writes; inspect deployment/DB status and safe logs; determine
whether a configuration, compatible image rollback or checked restore is needed;
recover and rerun health, logins, totals and chain verification. If audit verification
fails, preserve evidence and investigate before any rebuild; reset would erase it.
Do not repair a chain merely to make verification green. See [audit](audit.md) and
[security](security.md) for the guarantees and their limits.

## Known limitations and deferred work

There is no email delivery, self-service email recovery, online payment, upload,
adjustment-entry workflow, dashboard JSON API or scheduler endpoint. The importer
accepts a CSV directory and optional YAML header mapping, not XLSX files. Interests
are a fixed list; report weeks are Monday–Sunday. Active-member historical figures
use current status, and dashboard as_of does not reconstruct every past state.
Branch-register counts follow member.list and collection.list permissions for
each branch; denied metrics display a dash rather than a zero.
CMS seed event dates are fixed. Refreshing a page supplies current data; no push
updates exist. Free hosting can cold-start and needs operator-managed backup/expiry
work. [Security limitations](security.md#known-limitations-and-operator-checks) and
[manual accessibility limits](testing.md) remain relevant.

Potential later work includes audited adjustments, dynamic interests, notifications,
MFA and paid hosting/recovery. These are deferred, not delivered features. The owner
maintains [AI-USAGE.md](../AI-USAGE.md), final submission metadata and release access.
For maintenance, use the repository owner and
[issue tracker](https://github.com/bilal-rauf-dev/shiplens-branch-platform/issues).
