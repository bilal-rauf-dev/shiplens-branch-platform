"""Restore the migration-seeded reference rows for an empty sample import."""

from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.db import connection


def restore_reference_data():
    """Reuse the fixed data migrations so reset starts from the same baseline.

    Numeric migration filenames require import_module. Their seed functions only
    need the app registry and the editor's database connection alias.
    """
    editor = SimpleNamespace(connection=connection)
    import_module("apps.branches.migrations.0003_seed_cities").seed_cities(apps, editor)
    import_module("apps.volunteers.migrations.0002_seed_volunteer_roles").seed_roles(
        apps, editor
    )
