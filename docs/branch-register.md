# Branch register foundation

`create_branch` checks `branch.create`, validates the bilingual fields and creates
a Forming branch. The caller supplies a city, names, addresses and contacts;
the service supplies the code, status, actor and timestamps. Optional phone
numbers must already use E.164 format. Email addresses are stored in lowercase.

`ids.next_value("branch:KHI")` must run inside the business transaction. Django's
`get_or_create` handles simultaneous first inserts using an internal savepoint.
The function then locks that counter row, increments it and returns its value.
The lock lasts until the branch and its audit event commit. If validation or
audit writing fails, the counter increment rolls back too. Different cities
have independent counters. The two-digit padding grows naturally after 99.

`update_branch` locks the branch and permits only names, addresses and contacts.
Code, city, status, actors and dates cannot be supplied as editable fields.
Each successful edit records the before and after values in the same transaction.
PostgreSQL also rejects any actual change to an existing branch code, including
changes made outside the service. Names are unique ignoring case within a city.

The migrations seed ten bilingual cities. Branches created through the service
receive both names, actor fields and timestamps.

`transition` checks `branch.transition`, locks the current row and looks up its
state/action pair in `BRANCH_TRANSITIONS`. Only Forming → Active, Active → Paused,
Paused → Active, and any non-Closed state → Closed are allowed. Closed is terminal.
Pause and close require a trimmed reason of 5–300 characters; the bounds come
from `rules.get`. Activate and resume clear the current reason, while audit
history retains earlier reasons. Activation sets the Karachi opening date only
when missing; resuming preserves it. Closing records the Karachi closing date.
Actor, timestamp and audit history update in the same transaction.

`close_blockers` checks unsent collections and Submitted/Resubmitted/Returned
reports. A nonempty list prevents closing; see [finance](finance.md) and
[weekly reports](weekly-reports.md). Branch assignments
remain for history; the assignment service locks the branch and rejects new
assignments once it is Closed.

The register has city and branch create/edit screens for Super Admins. Finance
Reviewers see every branch read-only; Branch and HR Leads see assigned branches.
The list supports city/status filters and pages of 25. Only permitted staff see
a branch's history. Members and Unsent in the branch list/detail remain `—`
placeholders; those templates do not calculate counts. Use the scoped Members
page and dashboard's unsent figures for real data. City codes stay fixed after
creation so existing branch codes still match.

The POST-only `/en/branches/<id>/<action>/` endpoint (also available in Urdu)
redirects successful actions to the detail page, where a translated message is
shown once. Invalid reasons re-render the detail page with HTTP 400; invalid or
blocked transitions do the same with HTTP 409. The endpoint remains protected
by the route registry and CSRF checks.
