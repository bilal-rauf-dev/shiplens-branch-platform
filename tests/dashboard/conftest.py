from datetime import datetime

import pytest
from django.conf import settings
from django.core.management import call_command
from django.test import override_settings

from apps.accounts.models import User
from apps.core import clock as business_clock
from apps.seed.reference_data import restore_reference_data

AS_OF = datetime.fromisoformat("2026-10-31T23:00:00+05:00")


@pytest.fixture(autouse=True)
def dashboard_clock(clock):
    clock.move_to(AS_OF)


@pytest.fixture(scope="module")
def sample_data(django_db_setup, django_db_blocker):
    """Import once per test module; each test still rolls its own changes back."""
    with (
        django_db_blocker.unblock(),
        override_settings(
            PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
        ),
        business_clock.frozen_at(AS_OF),
    ):
        call_command("import_sample_data", str(settings.BASE_DIR / "sample_data"))
        User.objects.update(must_change_password=False)
    yield
    with django_db_blocker.unblock():
        call_command("flush", interactive=False, verbosity=0)
        restore_reference_data()
