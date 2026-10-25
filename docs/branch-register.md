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

Lifecycle transitions and register screens follow in P3 Steps 2 and 3.
