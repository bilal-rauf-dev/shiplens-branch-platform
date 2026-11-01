# Architecture

ShipLens is one Django application for public visitors and five staff roles.
Ujala Volunteer Network is the fictional demonstration organisation. Pages are
server rendered; dashboard figures refresh on page load. Collections and transfers
record offline activity. There is no payment provider, SPA or background worker.
The [ADRs](adr/0001-django-monolith.md) explain the main choices.

## C4 context

```mermaid
C4Context
    title ShipLens system context
    Person(visitor, "Public visitor", "Browse in English or Urdu and apply")
    Person(staff, "Staff", "Super Admin, Finance, Content, Branch and HR roles")
    Person(operator, "Owner / operator", "Deploys and maintains the demo")
    System(system, "ShipLens", "Public website and branch management")
    System_Ext(github, "GitHub Actions", "Repository checks")
    System_Ext(render, "Render", "Hosting and managed database")
    Rel(visitor, system, "Browses and applies", "HTTPS")
    Rel(staff, system, "Uses scoped staff pages", "HTTPS")
    Rel(operator, system, "Operates, backs up and rebuilds demo", "CLI")
    Rel(github, render, "Supplies deployment checks")
    Rel(render, system, "Hosts")
```

## C4 containers

```mermaid
C4Container
    title ShipLens deployment containers
    Person(operator, "Owner / operator", "Maintains the deployment")
    Container(browser, "Browser", "HTML, CSS, dashboard Chart.js", "English and Urdu pages")
    System_Boundary(hosting, "Render deployment") {
        Container(proxy, "TLS proxy", "Render edge", "Terminates public HTTPS")
        Container(web, "Web service", "Docker / Gunicorn / Django", "Templates, services, WhiteNoise and WeasyPrint")
        ContainerDb(db, "Database", "PostgreSQL 16", "Domain records, sessions, cache and audit")
    }
    Rel(browser, proxy, "Requests pages, static files and exports", "HTTPS")
    Rel(proxy, web, "Forwards requests with trusted headers", "HTTP")
    Rel(web, db, "Reads and writes through ORM", "PostgreSQL / production TLS default")
    Rel(operator, db, "Runs management commands and pg_dump", "External TLS connection")
```

WhiteNoise and WeasyPrint are libraries inside the web container, not independent
services. DatabaseCache shares rate limits across workers. No Redis is required.
The [deployment runbook](handover.md) describes operating the containers.

## Module map

| App | Responsibility |
| --- | --- |
| `core` | Clock, rule overrides, ID counters, middleware, shared forms, health and template helpers. |
| `accounts` | Email identity, sessions, central permissions, branch assignments and user/settings administration. |
| `branches` | Cities, branch codes, scoped register and branch lifecycle. |
| `volunteers` | Applications, spam guards, HR decisions, members, teams and volunteer roles. |
| `finance` | Offline collections, transfers, weekly report drafting, snapshots and review. |
| `dashboard` | Read-only KPI queries, period selection, role dashboards and chart data embedded in HTML. |
| `cms` | Working translations, sanitized Markdown and published content snapshots. |
| `publicsite` | Public selectors, pages, metadata, sitemap and robots; included through URL configuration. |
| `exports` | Scoped CSV and PDF generation, shared limits and export auditing. |
| `audit` | Request context, append-only history, hash verification and Super Admin viewer. |
| `seed` | CSV historical replay, guarded demo setup and operator-only rebuild. |

`config/` holds split settings, URL configuration and WSGI. `publicsite` has no
models or separate `INSTALLED_APPS` entry. See [permissions](permissions.md),
[security](security.md), [exports](exports.md), [public content](public-website.md),
[performance](performance.md), [CI](ci.md), [audit](audit.md) and the
[Urdu guide](i18n-glossary.md) for those concerns.

## Request lifecycle

Incoming middleware order below is copied from `config/settings/base.py`.
Responses unwind in reverse order; `process_view` runs after URL resolution.

1. `apps.core.middleware.RequestIdMiddleware` — validated UUID and request-local rules/assignment snapshots.
2. `csp.middleware.CSPMiddleware`.
3. `apps.core.middleware.SecurityHeadersMiddleware`.
4. `apps.core.middleware.HealthCheckMiddleware` — `/health` short-circuits here.
5. `django.middleware.security.SecurityMiddleware`.
6. `whitenoise.middleware.WhiteNoiseMiddleware` — serves static assets directly.
7. `django.contrib.sessions.middleware.SessionMiddleware`.
8. `django.middleware.locale.LocaleMiddleware`.
9. `django.middleware.common.CommonMiddleware`.
10. `django.contrib.auth.middleware.AuthenticationMiddleware`.
11. `apps.audit.middleware.AuditContextMiddleware`.
12. `apps.accounts.middleware.SessionTimeoutMiddleware`.
13. `apps.core.middleware.RouteRegistryMiddleware`.
14. `apps.accounts.middleware.MustChangePasswordMiddleware`.
15. `django.middleware.csrf.CsrfViewMiddleware`.
16. `django.contrib.messages.middleware.MessageMiddleware`.
17. `django.middleware.clickjacking.XFrameOptionsMiddleware`.
18. `axes.middleware.AxesMiddleware`.

The resolver chooses a view. The route registry allows explicitly public names,
looks up protected names in `ROUTE_ACTIONS`, and rejects unregistered names with
404. Anonymous private requests redirect to login; disallowed roles get 403.
Views validate forms and use scoped selectors before object lookup. Out-of-scope
identifiers return 404. Services recheck permissions, take transaction/row locks,
enforce state rules, write the change and call `audit.record` in the same transaction.
Templates render the result; successful form writes normally redirect. Validation
and state conflicts normally return 400 and 409. The route reference records methods.

For example, Finance approval locks the branch then report, verifies status and
revision, records `report.approved`, changes to Locked and records `report.locked`.
Both changes commit together. The second event has a system actor. The next
dashboard request reads the approved revision's stored lines.

The health shortcut runs before sessions, host validation and HTTPS redirects so
internal HTTP/IP readiness probes work. Its outer request-ID, CSP and security
header layers still apply. See [security](security.md) for the boundaries.

## ER diagram from the real models

Generated by `python bin/export_model_diagram.py` with the normal Django environment
configured; no database connection is needed. The script reads concrete Django
model metadata, including inherited fields, from every `apps/*/models.py` model.
Each block includes all stored fields; each relationship is labelled with its field
name. Nullable links use an optional parent end; one-to-one links have at most one
child. `AuditLog.branch_id` and entity identifiers are scalar history identifiers,
not FKs. Framework sessions, auth/content types and Axes models are outside this
application-model diagram; DatabaseCache is a command-created table, not a model.

<!-- ER:START -->
```mermaid
erDiagram
    applications {
        BigAutoField id PK
        CharField reference
        CharField full_name
        CharField email
        CharField phone
        DateField date_of_birth
        BooleanField guardian_consent
        ForeignKey preferred_branch_id FK
        ArrayField interests
        ArrayField availability
        TextField motivation
        CharField preferred_language
        DateTimeField consent_at
        CharField status
        BooleanField possible_duplicate
        ForeignKey duplicate_of_application_id FK
        ForeignKey duplicate_of_member_id FK
        ForeignKey decided_by_id FK
        DateTimeField decided_at
        CharField decision_note
        OneToOneField member_id FK
        CharField ip_hash
        DateTimeField created_at
        DateTimeField updated_at
    }
    audit_log {
        BigAutoField id PK
        DateTimeField occurred_at
        ForeignKey actor_id FK
        CharField actor_label
        CharField actor_role
        CharField action
        CharField entity_type
        PositiveBigIntegerField entity_id
        CharField entity_label
        PositiveBigIntegerField branch_id
        JSONField before
        JSONField after
        JSONField metadata
        GenericIPAddressField ip
        CharField user_agent
        UUIDField request_id
        CharField prev_hash
        CharField hash
    }
    branches {
        BigAutoField id PK
        CharField code
        ForeignKey city_id FK
        CharField name_en
        CharField name_ur
        CharField address_en
        CharField address_ur
        CharField phone
        CharField email
        CharField status
        CharField status_reason
        DateField opened_on
        DateField closed_on
        ForeignKey created_by_id FK
        ForeignKey updated_by_id FK
        DateTimeField created_at
        DateTimeField updated_at
    }
    cities {
        BigAutoField id PK
        CharField code
        CharField name_en
        CharField name_ur
        DateTimeField created_at
        DateTimeField updated_at
    }
    collections {
        BigAutoField id PK
        CharField reference
        ForeignKey branch_id FK
        CharField entry_type
        ForeignKey adjusts_collection_id FK
        DateField collection_date
        DecimalField amount
        CharField method
        CharField receipt_no
        ForeignKey collected_by_member_id FK
        CharField source_note
        ForeignKey transfer_id FK
        DateTimeField voided_at
        ForeignKey voided_by_id FK
        CharField void_reason
        ForeignKey created_by_id FK
        DateTimeField created_at
        DateTimeField updated_at
    }
    content_items {
        BigAutoField id PK
        CharField type
        CharField slug
        CharField status
        BooleanField has_unpublished_changes
        JSONField published_snapshot
        DateTimeField published_at
        DateTimeField event_start
        DateTimeField event_end
        CharField location_en
        CharField location_ur
        ForeignKey branch_id FK
        CharField image_path
        IntegerField sort_order
        ForeignKey created_by_id FK
        ForeignKey updated_by_id FK
        DateTimeField created_at
        DateTimeField updated_at
    }
    content_translations {
        BigAutoField id PK
        ForeignKey content_id FK
        CharField locale
        CharField title
        CharField summary
        TextField body_md
        TextField body_html
    }
    id_sequences {
        CharField key PK
        PositiveIntegerField last_value
        DateTimeField updated_at
    }
    members {
        BigAutoField id PK
        CharField member_id
        OneToOneField application_id FK
        ForeignKey branch_id FK
        ForeignKey team_id FK
        ForeignKey volunteer_role_id FK
        CharField full_name
        CharField email
        CharField phone
        CharField status
        DateField joined_on
        DateField left_on
        CharField notes
        ForeignKey created_by_id FK
        ForeignKey updated_by_id FK
        DateTimeField created_at
        DateTimeField updated_at
    }
    system_settings {
        CharField key PK
        JSONField value
        ForeignKey updated_by_id FK
        DateTimeField updated_at
    }
    teams {
        BigAutoField id PK
        ForeignKey branch_id FK
        CharField name
        BooleanField is_active
    }
    transfers {
        BigAutoField id PK
        CharField reference
        ForeignKey branch_id FK
        DateField transfer_date
        CharField bank_reference
        DecimalField total_amount
        TextField note
        ForeignKey created_by_id FK
        DateTimeField created_at
    }
    user_branch_assignments {
        BigAutoField id PK
        ForeignKey user_id FK
        ForeignKey branch_id FK
        ForeignKey created_by_id FK
        DateTimeField created_at
    }
    users {
        BigAutoField id PK
        CharField password
        DateTimeField last_login
        CharField email
        CharField full_name
        CharField role
        BooleanField is_active
        BooleanField is_demo
        BooleanField must_change_password
        CharField preferred_language
        DateTimeField date_joined
        DateTimeField updated_at
    }
    volunteer_roles {
        BigAutoField id PK
        CharField code
        CharField name_en
        CharField name_ur
        BooleanField is_active
        PositiveIntegerField sort_order
    }
    weekly_report_lines {
        BigAutoField id PK
        ForeignKey report_id FK
        PositiveIntegerField revision
        ForeignKey collection_id FK
        CharField reference
        DateField collection_date
        CharField method
        DecimalField amount
    }
    weekly_reports {
        BigAutoField id PK
        ForeignKey branch_id FK
        DateField week_start
        DateField week_end
        CharField status
        IntegerField revision
        JSONField narrative
        JSONField snapshot
        CharField snapshot_hash
        DateTimeField submitted_at
        ForeignKey submitted_by_id FK
        DateTimeField reviewed_at
        ForeignKey reviewed_by_id FK
        CharField review_comment
        DateTimeField approved_at
        ForeignKey approved_by_id FK
        DateTimeField locked_at
        DateTimeField created_at
        DateTimeField updated_at
    }
    branches ||--o{ applications : "preferred_branch"
    applications |o--o{ applications : "duplicate_of_application"
    members |o--o{ applications : "duplicate_of_member"
    users |o--o{ applications : "decided_by"
    members |o--o| applications : "member"
    users |o--o{ audit_log : "actor"
    cities ||--o{ branches : "city"
    users |o--o{ branches : "created_by"
    users |o--o{ branches : "updated_by"
    branches ||--o{ collections : "branch"
    collections |o--o{ collections : "adjusts_collection"
    members |o--o{ collections : "collected_by_member"
    transfers |o--o{ collections : "transfer"
    users |o--o{ collections : "voided_by"
    users ||--o{ collections : "created_by"
    branches |o--o{ content_items : "branch"
    users ||--o{ content_items : "created_by"
    users ||--o{ content_items : "updated_by"
    content_items ||--o{ content_translations : "content"
    applications |o--o| members : "application"
    branches ||--o{ members : "branch"
    teams |o--o{ members : "team"
    volunteer_roles ||--o{ members : "volunteer_role"
    users |o--o{ members : "created_by"
    users |o--o{ members : "updated_by"
    users ||--o{ system_settings : "updated_by"
    branches ||--o{ teams : "branch"
    branches ||--o{ transfers : "branch"
    users ||--o{ transfers : "created_by"
    users ||--o{ user_branch_assignments : "user"
    branches ||--o{ user_branch_assignments : "branch"
    users ||--o{ user_branch_assignments : "created_by"
    weekly_reports ||--o{ weekly_report_lines : "report"
    collections ||--o{ weekly_report_lines : "collection"
    branches ||--o{ weekly_reports : "branch"
    users |o--o{ weekly_reports : "submitted_by"
    users |o--o{ weekly_reports : "reviewed_by"
    users |o--o{ weekly_reports : "approved_by"
```
<!-- ER:END -->

## Schema protections and plan differences

Read model `Meta.constraints` and migrations together: branch/member identity,
same-branch team membership, sent collections, transfers, locked reports/lines
and audit history have migration-level guards as well as service checks.
The [business-rule catalogue](business-rules.md) names the enforcement and tests.

Compared with planning/10 and planning/18: `/health` is the only machine endpoint;
charts receive JSON embedded in HTML, and draft generation uses pages or a command.
There is no `/internal/generate-drafts` or dashboard JSON API. There is no generic
`services/` package: apps mostly use `services.py`, with finance report modules
alongside it. No scheduler or outbound notification hook is required. Identifiers
use ORM `get_or_create` and locked counters, not a raw SQL counter upsert.
