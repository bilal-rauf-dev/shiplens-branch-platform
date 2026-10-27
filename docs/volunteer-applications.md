# Public volunteer applications

The public form is available in English and Urdu at `/en/get-involved/` and
`/ur/get-involved/`. It uses a normal server-rendered POST with CSRF protection.
Successful submissions redirect to a generic thanks page that displays only a
reference. That page never looks up an applicant or discloses duplicate status.

`ApplicationForm` implements BR-040–BR-050. Names are trimmed and spaces collapsed
before length checks; Python's Unicode letter/mark categories accept Urdu without
an extra dependency. Emails are lowercased and Pakistani mobile numbers normalised
to `+923…`. Ages count completed birthdays on the Karachi business date. Consent
is required below 18, and privacy consent is required for every application.
Only Active or Forming branches are selectable. The submission service locks and
re-checks the branch, so a pause/close after form validation still prevents a write.
Interests are a fixed list until P10 supplies published programs.

The browser checks email type, mobile-number pattern, name and motivation lengths,
inclusive birth-date bounds and required privacy consent using HTML attributes.
Date bounds use the same completed-birthday rules and Karachi clock as the server,
including leap days. No JavaScript is needed. Conditional guardian consent and
choosing at least one item from a checkbox group remain server checks; marking
each checkbox required would incorrectly require every choice. All submitted
values are still validated on the server, including direct POSTs.

The signed `apply-form` timestamp must be between the configured minimum fill
time and two hours old. A filled honeypot or invalid timestamp receives the same
thanks-page shape with a random reference; neither allocates an application ID.
The spam event records its reason only. Rate limits count every POST: the current
hourly setting (default 5) and 20 per day, keyed through the shared proxy-aware
client-IP helper. Django's database cache does not atomically increment counters,
so `application_rate_limited` locks the `IdSequence` row `application:rate-limit`
around both django-ratelimit calls. That row is only a mutex: its value stays zero.
No additional cache server or dependency is required.

`submit_application` reserves the yearly `APP-YYYY-NNNNN` reference, checks for
matching pending applications or non-Left members, saves the application and
writes its audit event in one transaction. Duplicate matches are deterministic
(oldest matching record); both pointers are set when both kinds of match exist.
The IP is stored as SHA-256 of the resolved address plus `SECRET_KEY`. Submission
audits contain only the reference and branch; public audit events force an anonymous
actor and omit the raw address and user agent, even for signed-in visitors.

The schema includes application status/member and decline-note checks, motivation
length, team-name uniqueness, the team/branch composite foreign key, immutable
member IDs, current-member email uniqueness and Left/date consistency. Four roles
are seeded with Urdu names. There is no public access to stored personal data.

## Teams and volunteer roles

HR Leads create, rename and deactivate teams in their assigned branches through
the Teams navigation. Super Admins can manage all teams. Branch Leads see assigned
teams without write controls, following the permission matrix. The branch comes
from a scoped URL lookup, never from a form field. Names remain unique within a
branch after deactivation. Services lock branches before teams, matching acceptance
and serializing competing creates and renames. Each write commits together with
its `team.created` or `team.updated` audit event.

Super Admins manage bilingual volunteer-role labels, ordering and deactivation
through Volunteer roles. New codes use the existing locked counter to generate
`ROLE-00001`, `ROLE-00002`, etc.; the four seeded codes remain unchanged. Forms
never accept role codes or active state. Each role write records
`volunteer_role.created` or `volunteer_role.updated` in the same transaction.
Deactivation excludes teams and roles from new acceptance choices while existing
members keep their links. Successful forms redirect to the list with a translated
message.

BR-056 already has a PostgreSQL composite foreign key in migration
`0003_member_integrity`: `(members.team_id, members.branch_id)` references
`(teams.id, teams.branch_id)`. It prevents cross-branch assignment even through
direct SQL. Django's ordinary foreign key cannot express that pair, so the existing
migration uses `RunSQL`; no replacement migration is needed. BR-057's
case-insensitive unique constraint also already exists.

## HR decision services

`accept_application` scopes and locks the application before checking it is still
Pending. Only an assigned HR Lead can accept or decline; Super Admins retain
read-only access to decisions. Acceptance locks the current branch and rejects a
Closed branch. An optional team must be active and belong to that branch, and the
selected role must be active. Both are rechecked under row locks. The service
reserves `M-YYYY-NNNNN` using the Karachi acceptance year,
creates an Active member, links the application and records the deciding actor
and time. It returns the new member.

The member, application, counter and both events (`application.accepted`, then
`member.created`) commit together. A failure in either audit write rolls back the
entire decision. The application lock prevents two reviewers accepting the same
record; the counter lock also serializes member-ID allocation across branches.
Existing current-member email uniqueness remains enforced by the database.

`decline_application` takes the same scoped application lock and records a
trimmed internal reason of 5–500 characters, with bounds read through `rules.get`.
`reassign_branch` requires the source application to be in scope and Pending;
the destination can be any Active or Forming branch, as specified in the task and
RBAC matrix. It may therefore leave the calling HR Lead's scope after the move.
Both services update the timestamp and audit the change in their transaction.
Accepted and Declined applications reject further decisions or reassignment.

`InvalidTransition` is shared with branch services through `core.exceptions`.

## HR review pages

HR lands at `/en/app/applications/` after login (with the equivalent Urdu route).
The list defaults to Pending, with Accepted/Declined tabs, a scoped branch filter,
newest-first ordering and pages of 25. Every lookup applies the central queryset
scope before resolving a record ID. Finance, Content and Branch Leads cannot open
application pages. Super Admins can read every application and reassign Pending
ones as granted by the matrix; only scoped HR Leads can accept or decline.

Detail pages show age instead of date of birth and include the shared audit-history
partial. Duplicate matches are looked up through the viewer's application/member
scope; an inaccessible match never exposes its reference, name or link. A small
read-only member detail route provides the matched-member link destination.
Member editing remains in P5 Step 3.

Acceptance forms offer teams from the application's branch and existing roles.
Decline reasons use the same configured bounds as the service. Reassignment offers
Active/Forming targets. Successful POSTs redirect with a translated one-time
message. If an HR Lead reassigns outside their scope, the redirect goes back to the
list. Invalid forms and business validation errors re-render detail with HTTP 400;
terminal decisions and closed-branch acceptance return HTTP 409. Acceptance also
reports current-member email conflicts in plain language while retaining the
database uniqueness constraint. Review pages use private, no-store responses.

## Member register and search

`/en/app/members/` and `/ur/app/members/` show a scoped register for Super Admin,
Branch Lead and HR Lead. Finance and Content roles receive 403. The default is
Active members, newest creation first. Choose All statuses to include Inactive and
Left members. Name sorting is case-insensitive; name and joined-date sorts work in
both directions and use the primary key to break ties consistently across pages.

`MemberFilterForm` validates GET parameters before `selectors.search_members`
applies them. The selector always scopes members before applying search and the
AND-combined branch, team, role, status and inclusive joined-date filters. Invalid
or inaccessible filter values show errors and no results. Branch and team choices
are scoped too; inactive teams and roles remain selectable for historical records.
Each choice list is loaded once for both validation and rendering.

Search uses case-insensitive substring matches on name, email and member ID.
Phone-shaped queries also match stored phone digits; spaces, dashes, parentheses
and the leading local zero in `03…` are normalized for the search. Pagination keeps
every GET parameter except the previous page number, and each page holds 25
members. Below 640px, CSS turns each table row into a labelled card without
JavaScript. Responses are private and no-store because members contain PII.

Migration `0004_member_search_indexes` enables `pg_trgm` before adding GIN indexes
on `UPPER(full_name)` and `UPPER(email)`, matching Django's PostgreSQL `icontains`
SQL. A separate `LOWER(full_name)` B-tree supports name ordering. Branch/joined,
joined, status and creation-time indexes cover filters and ordering. Existing team
and role foreign-key indexes, the member-ID unique index and branch/status index
are retained without duplicates. `django.contrib.postgres` is enabled so Django
registers expression-index operator classes correctly; this adds no dependency.

`pytest -m performance tests/volunteers/test_member_search.py` bulk-creates exactly
5,000 members, warms template compilation, then measures a fully rendered scoped
view with all filters. It enforces at most 8 queries and under 300ms. Fixture setup
and authentication/session middleware are excluded from that view budget; separate
HTTP tests cover the complete authenticated route and role/scope enforcement.
