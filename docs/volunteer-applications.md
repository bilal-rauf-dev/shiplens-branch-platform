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

## HR decision services

`accept_application` scopes and locks the application before checking it is still
Pending. Only an assigned HR Lead can accept or decline; Super Admins retain
read-only access to decisions. Acceptance locks the current branch and rejects a
Closed branch. An optional team must exist in that branch, and the selected role
must exist. The service reserves `M-YYYY-NNNNN` using the Karachi acceptance year,
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
Member list/search and editing remain in P5.

Acceptance forms offer teams from the application's branch and existing roles.
Decline reasons use the same configured bounds as the service. Reassignment offers
Active/Forming targets. Successful POSTs redirect with a translated one-time
message. If an HR Lead reassigns outside their scope, the redirect goes back to the
list. Invalid forms and business validation errors re-render detail with HTTP 400;
terminal decisions and closed-branch acceptance return HTTP 409. Acceptance also
reports current-member email conflicts in plain language while retaining the
database uniqueness constraint. Review pages use private, no-store responses.
