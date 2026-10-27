"""Read-only infrastructure checks."""

from django.db import connection
from django.db.backends.base.base import NO_DB_ALIAS


def check_database():
    """Run the health probe without changing the application's connection options."""
    # This copy still targets the configured database. Its temporary alias skips
    # contrib.postgres type registration, which expects a registered connection
    # and is unnecessary for SELECT 1.
    probe = connection.copy(alias=NO_DB_ALIAS)
    options = probe.settings_dict["OPTIONS"]
    options["connect_timeout"] = 2
    # PostgreSQL receives the query timeout as a connection option, in milliseconds.
    options["options"] = (
        f"{options.get('options', '')} -c statement_timeout=2000".strip()
    )
    try:
        with probe.cursor() as cursor:
            # The explicit SELECT 1 health probe is required by P1 / plan 15 §2.
            cursor.execute("SELECT 1")
            return cursor.fetchone() == (1,)
    finally:
        probe.close()
