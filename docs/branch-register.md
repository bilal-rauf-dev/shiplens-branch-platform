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

`close_blockers` currently returns an empty list. P6 will add unsent collections
and P7 will add open reports. A nonempty list prevents closing. Branch assignments
remain for history; the assignment service locks the branch and rejects new
assignments once it is Closed.

The POST-only `/en/branches/<id>/<action>/` endpoint (also available in Urdu)
returns translated text: 200 on success, 409 for an invalid transition or blocked
close, and 400 for invalid reasons. It is protected by the route registry and
CSRF checks. Register screens and their forms follow in P3 Step 3.
