import runpy
from importlib import import_module

import pytest
from django.conf import settings


@pytest.mark.parametrize("render_hostname", [None, "shiplens-test.onrender.com"])
def test_render_hostname_added_to_hosts_and_origins(monkeypatch, render_hostname):
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "example.com, localhost")
    monkeypatch.setenv("CSRF_TRUSTED_ORIGINS", "https://example.com")
    monkeypatch.delenv("RENDER_EXTERNAL_HOSTNAME", raising=False)
    if render_hostname:
        monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", render_hostname)

    configuration = runpy.run_path(str(settings.BASE_DIR / "config/settings/base.py"))

    expected_hosts = ["example.com", "localhost"]
    expected_origins = ["https://example.com"]
    if render_hostname:
        expected_hosts.append(render_hostname)
        expected_origins.append(f"https://{render_hostname}")
    assert configuration["ALLOWED_HOSTS"] == expected_hosts
    assert configuration["CSRF_TRUSTED_ORIGINS"] == expected_origins


@pytest.mark.parametrize(
    "module_name", ["config.settings.base", "config.settings.prod"]
)
def test_base_and_production_keep_argon2_first(module_name):
    configuration = import_module(module_name)
    assert configuration.PASSWORD_HASHERS[0] == (
        "django.contrib.auth.hashers.Argon2PasswordHasher"
    )
