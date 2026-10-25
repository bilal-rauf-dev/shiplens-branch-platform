import pytest
import time_machine
from django.core.management import call_command
from django.db import connection, transaction


@pytest.fixture(scope="session", autouse=True)
def audit_test_database(django_db_setup, django_db_blocker):
    """Create DatabaseCache and allow Django's test-only flush to clear audit rows."""
    with django_db_blocker.unblock():
        call_command("createcachetable", verbosity=0)
    original_flush = connection.ops.execute_sql_flush

    def flush_test_database(sql_list):
        # Only test database cleanup may bypass the TRUNCATE guard. Re-enable it
        # in the same transaction; failures roll back the trigger change too.
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "ALTER TABLE audit_log DISABLE TRIGGER audit_guard_truncate"
                )
            original_flush(sql_list)
            with connection.cursor() as cursor:
                cursor.execute(
                    "ALTER TABLE audit_log ENABLE TRIGGER audit_guard_truncate"
                )

    connection.ops.execute_sql_flush = flush_test_database
    try:
        yield
    finally:
        connection.ops.execute_sql_flush = original_flush


@pytest.fixture
def clock():
    """Freeze the shared clock without changing the machine's wall clock."""
    with time_machine.travel("2026-10-25T12:00:00+05:00", tick=False) as traveller:
        yield traveller
