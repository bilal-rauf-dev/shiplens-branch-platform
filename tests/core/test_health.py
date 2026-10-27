from copy import deepcopy
from unittest.mock import MagicMock, patch

import pytest
from django.db import InterfaceError, OperationalError, connection
from django.db.backends.base.base import NO_DB_ALIAS
from django.urls import reverse

from apps.core import selectors


@pytest.mark.django_db
def test_t_ops_health(client, clock, monkeypatch):
    clock.move_to("2026-10-25T20:30:00+00:00")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abcdef1234567890")
    monkeypatch.setenv("GIT_SHA", "7654321fedcba")

    response = client.get("/health", HTTP_ACCEPT_LANGUAGE="ur")

    assert reverse("health") == "/health"
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "db": "ok",
        "version": "abcdef1",
        "time": "2026-10-25T20:30:00Z",
    }
    assert response["Cache-Control"] == "no-store"


@pytest.mark.parametrize("error_type", [OperationalError, InterfaceError, RuntimeError])
def test_t_ops_health_dbdown(client, error_type):
    probe = MagicMock()
    probe.settings_dict = {"OPTIONS": {}}
    probe.cursor.side_effect = error_type(
        "Traceback: secret database connection details"
    )

    with patch.object(connection, "copy", return_value=probe):
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "db": "error"}
    assert "traceback" not in response.text.lower()
    assert "secret" not in response.text
    assert response["Cache-Control"] == "no-store"
    probe.close.assert_called_once_with()


@pytest.mark.parametrize(
    "render_commit,git_sha,expected",
    [(None, "7654321abcdef", "7654321"), (None, None, "dev"), ("", "123", "123")],
)
def test_health_version_fallbacks(
    client, clock, monkeypatch, render_commit, git_sha, expected
):
    for name, value in [("RENDER_GIT_COMMIT", render_commit), ("GIT_SHA", git_sha)]:
        monkeypatch.delenv(name, raising=False)
        if value is not None:
            monkeypatch.setenv(name, value)
    monkeypatch.setattr(selectors, "check_database", lambda: True)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["version"] == expected


def test_health_probe_timeouts_and_cleanup():
    original_options = deepcopy(connection.settings_dict["OPTIONS"])
    probe = MagicMock()
    probe.settings_dict = {"OPTIONS": {"options": "-c lock_timeout=5000"}}
    cursor = probe.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (1,)

    with patch.object(connection, "copy", return_value=probe) as copy_connection:
        assert selectors.check_database() is True

    copy_connection.assert_called_once_with(alias=NO_DB_ALIAS)

    assert probe.settings_dict["OPTIONS"] == {
        "connect_timeout": 2,
        "options": "-c lock_timeout=5000 -c statement_timeout=2000",
    }
    assert connection.settings_dict["OPTIONS"] == original_options
    cursor.execute.assert_called_once_with("SELECT 1")
    probe.close.assert_called_once_with()


def test_health_requires_get(client):
    response = client.post("/health")

    assert response.status_code == 405
    assert response["Allow"] == "GET"
    assert response["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_t_ops_health_internal_http_in_production(client, settings):
    settings.SECURE_SSL_REDIRECT = True
    settings.ALLOWED_HOSTS = ["example.com"]

    response = client.get("/health", HTTP_HOST="127.0.0.1:8000")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert reverse("health") == "/health"


@pytest.mark.parametrize("path", ["/en/", "/health/", "/healthcheck", "/en/health"])
def test_t_sec_host_validation_outside_health(client, settings, path):
    settings.SECURE_SSL_REDIRECT = True
    settings.ALLOWED_HOSTS = ["example.com"]

    response = client.get(path, HTTP_HOST="127.0.0.1:8000")

    assert response.status_code == 400


def test_t_sec_https_redirect_outside_health(client, settings):
    settings.SECURE_SSL_REDIRECT = True
    settings.ALLOWED_HOSTS = ["example.com"]

    response = client.get("/en/", HTTP_HOST="example.com")

    assert response.status_code == 301
    assert response.url == "https://example.com/en/"
