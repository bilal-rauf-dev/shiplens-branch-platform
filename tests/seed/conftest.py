import pytest

from tests.accounts.conftest import TEST_PASSWORD


@pytest.fixture(autouse=True)
def demo_settings(settings, clock):
    settings.DEMO_MODE = True
    settings.DEMO_PASSWORD = TEST_PASSWORD
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    clock.move_to("2026-10-31T23:00:00+05:00")
