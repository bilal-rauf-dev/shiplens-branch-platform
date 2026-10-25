"""Read-only infrastructure checks."""

from django.db import connection


def check_database():
    """Run the health probe without changing the application's connection options."""
    probe = connection.copy(alias="health")
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
