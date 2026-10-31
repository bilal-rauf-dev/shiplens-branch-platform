# Audit log

`apps.audit.record(actor, action, ...)` appends a history row inside the caller's
`transaction.atomic()` block (BR-130). A failed business transaction rolls its audit
row back too. Authentication services surround Django signals with the same
transaction; receivers also open an atomic block for framework callers. Branch
assignment creation is audited once; repeated assignment requests are idempotent.

## Request context and sensitive data

`AuditContextMiddleware` runs after authentication and before session timeouts and
route checks. A context variable carries only validated client IP, the first 200
user-agent characters, UUID request ID and whether the request was authenticated.
The middleware resets the variable on success and exceptions. The IP resolver is
the same right-counted trusted-proxy helper used by Axes and rate-limit keys.

An explicit user actor gets their email and role snapshotted. With no actor, a
request that started anonymously uses `anonymous`; a command or an authenticated
request with no actor uses `system`. No request bodies, passwords or cookies are
copied. Failed-login metadata contains only normalized email. Keys containing
`password`, `token` or `secret` (case-insensitive) are replaced with `[REDACTED]`
recursively in before/after/metadata. The diff helper keeps only changed fields,
including additions and removals (BR-133).

## Hash chain and SQL exceptions

Every append acquires a fixed `pg_advisory_xact_lock` before reading the preceding
row. The lock lasts until the outer transaction ends, so concurrent transactions
cannot select the same predecessor (BR-132). The writer reserves its ID using the
table's PostgreSQL sequence before hashing. Sequence gaps after rollback are normal.

The hash is SHA-256 of the previous hash concatenated with canonical JSON of every
concrete stored field except `hash`, including the ID and `prev_hash`. Genesis is
64 zeroes. JSON keys are sorted, separators fixed and Unicode preserved. Decimal,
date and UUID values become strings; aware timestamps use UTC ISO 8601 so reading
PostgreSQL's UTC values reproduces the business clock's original instant.

The explicit P2 advisory-lock requirement needs two fixed, parameterized SQL
queries in the writer: the advisory lock and sequence ID reservation. These are
narrow exceptions to AGENTS.md's general no-SQL-outside-migrations rule; audit
inserts and reads use the ORM. Trigger SQL and its reverse live in a migration.

`verify_chain()` reads one ordered snapshot and returns `(ok, first_bad_id)`.
`manage.py verify_audit_chain` exits unsuccessfully with the offending ID when
verification fails. Verification does not itself append a row.

## Immutability and limitations

PostgreSQL triggers reject UPDATE, DELETE and TRUNCATE (BR-131), including ORM and
raw SQL attempts. No application user, including Super Admin, can remove audit rows through HTTP.
No audit mutation or reset endpoint exists. The database
owner can still disable/drop triggers and rewrite history; this is tamper
resistance, not protection against a malicious database owner. The hash chain
detects altered rows/links, but needs an independently retained tip to detect
removal of the entire tail after bypassing the database guards.

Permission denials use DatabaseCache with a 60-second timestamp per user/route.
The same advisory lock serializes cache checks; expiration rounding cannot shorten
the interval. The audit row and database-cache update commit together. The 403 is
raised after that transaction so denied attempts remain recorded.

Tests deliberately disable the change guard to prove tamper detection. The test
database's flush helper disables only the TRUNCATE guard during Django cleanup and
re-enables it in the same transaction. This exception exists only in test fixtures;
ordinary test and application operations still encounter all guards.

## Operator-only demo database rebuild

`apps.seed.services._reset_tables()` is the one additional raw-SQL exception,
**unreachable when DEMO_MODE=false**. `seed_demo --reset` is run by the operator from a shell, never by an application
user. It rebuilds the demo database from the authored history after checking
`DEMO_MODE` and a `DEMO_PASSWORD` of at least 12 characters. There is no HTTP reset
view, URL, permission or settings-page control. It disables USER triggers on a fixed list of application tables,
truncates domain data, audit history, counters, settings overrides, sessions, Axes
records and the database cache with `RESTART IDENTITY CASCADE`, and re-enables the
triggers before importing history. All of this, including the re-import and demo
password setup, runs inside one PostgreSQL transaction. A failure restores the old
data, sequences and enabled triggers. Foreign-key system triggers are never disabled.

The importer restores the migration-seeded cities and volunteer roles as its
reference baseline, then runs each CSV event through the real service at its
historical business-clock instant. Spreadsheet members have a null system actor
and an audited `source: spreadsheet import` marker. Reset deliberately starts a
new fictional audit history; it is unsuitable for a deployment containing real
operational data. Truncating settings overrides restores the defaults in settings.
