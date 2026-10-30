"""Operator seeding and demo-database rebuilds, never application-user actions."""

from pathlib import Path

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction

from apps import audit
from apps.accounts.models import User
from apps.core import clock
from apps.core.models import IdSequence, SystemSetting
from apps.seed.importer import import_sample_data


def require_demo_configuration():
    """Fail closed before either importing demo accounts or truncating any table."""
    if not settings.DEMO_MODE:
        raise PermissionDenied("Demo seeding and reset require DEMO_MODE=true.")
    if len(settings.DEMO_PASSWORD) < 12:
        raise ValueError("DEMO_PASSWORD must contain at least 12 characters.")


def _reset_tables():
    """P8 SQL exception: transactional reset, unreachable when DEMO_MODE=false.

    Only user triggers are disabled; foreign-key/system triggers remain active.
    PostgreSQL rolls TRUNCATE, sequences and trigger DDL back with the import if
    anything fails. Names below are fixed application tables, never user input.
    """
    require_demo_configuration()
    if not connection.in_atomic_block:
        raise AssertionError("Demo reset requires an outer transaction.")
    tables = (
        "content_translations",
        "content_items",
        "users",
        "user_branch_assignments",
        "cities",
        "branches",
        "teams",
        "volunteer_roles",
        "members",
        "applications",
        "collections",
        "transfers",
        "weekly_reports",
        "weekly_report_lines",
        "audit_log",
        "id_sequences",
        "system_settings",
        "django_session",
        "axes_accessattempt",
        "axes_accesslog",
        "axes_accessfailurelog",
        "shiplens_cache",
    )
    with connection.cursor() as cursor:
        for table in tables:
            cursor.execute(f'ALTER TABLE "{table}" DISABLE TRIGGER USER')
        quoted = ", ".join(f'"{table}"' for table in tables)
        cursor.execute(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE")
        for table in tables:
            cursor.execute(f'ALTER TABLE "{table}" ENABLE TRIGGER USER')


def seed_demo(*, if_empty=False, reset=False, triggered_by=""):
    """Rebuild the demo database from authored history when reset is requested.

    The operator runs seed_demo --reset from a shell, never as an application user.
    Startup may seed an empty demo; no HTTP view calls this service.
    """
    require_demo_configuration()
    with transaction.atomic():
        # Serialize concurrent startup calls across gunicorn/deploy processes.
        IdSequence.objects.get_or_create(key="demo:seed-lock")
        IdSequence.objects.select_for_update().get(key="demo:seed-lock")
        if (
            if_empty
            and not reset
            and SystemSetting.objects.filter(key="demo_seeded").exists()
        ):
            return False
        if reset:
            _reset_tables()
            IdSequence.objects.get_or_create(key="demo:seed-lock")
        import_sample_data(Path(settings.BASE_DIR) / "sample_data")
        admin = User.objects.get(email="superadmin.demo@shiplens.test")
        for user in User.objects.order_by("pk"):
            user.set_password(settings.DEMO_PASSWORD)
            user.is_demo = True
            user.must_change_password = False
            user.updated_at = clock.now()
            user.save(
                update_fields=[
                    "password",
                    "is_demo",
                    "must_change_password",
                    "updated_at",
                ]
            )
            audit.record(
                None,
                "user.demo_configured",
                entity=user,
                after={"is_demo": True, "must_change_password": False},
            )
        # System settings have deployment defaults in rules.py. Truncating their
        # overrides restores those defaults; this marker is the only new row.
        SystemSetting.objects.create(
            key="demo_seeded",
            value=clock.now().isoformat(),
            updated_by=admin,
            updated_at=clock.now(),
        )
        audit.record(
            None,
            "demo.reset" if reset else "demo.seeded",
            metadata={"triggered_by": triggered_by},
        )
        return True
