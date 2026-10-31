import json
import logging
import runpy

import pytest
from django.db import connection

from apps.core.context import request_id
from apps.core.logging import SafeJsonFormatter
from config.settings import base


def test_json_logs_redact_sensitive_values_and_keep_request_id():
    formatter = SafeJsonFormatter()
    record = logging.LogRecord(
        "app.operation",
        logging.INFO,
        __file__,
        1,
        "Failed for %s %s password=NeverLogThis!",
        ("private@example.com", "+923001112233"),
        None,
    )
    token = request_id.set("90d250cb-213b-45de-9368-c088de2fb150")
    try:
        text = formatter.format(record)
    finally:
        request_id.reset(token)
    event = json.loads(text)
    assert event["request_id"] == "90d250cb-213b-45de-9368-c088de2fb150"
    for secret in ("private@example.com", "+923001112233", "NeverLogThis!"):
        assert secret not in text


def test_json_error_logs_exclude_tracebacks_and_request_paths():
    record = logging.LogRecord(
        "django.request",
        logging.ERROR,
        __file__,
        1,
        "Internal Server Error: /private@example.com?password=secret",
        (),
        (RuntimeError, RuntimeError("private database details"), None),
    )
    event = json.loads(SafeJsonFormatter().format(record))
    assert event["message"] == "HTTP request failed"
    assert event["exception_type"] == "RuntimeError"
    assert "private" not in json.dumps(event)


@pytest.mark.django_db
def test_database_statements_have_a_timeout():
    with connection.cursor() as cursor:
        cursor.execute("SHOW statement_timeout")
        assert cursor.fetchone()[0] == "15s"


def test_health_also_has_request_correlation(client, monkeypatch):
    monkeypatch.setattr("apps.core.selectors.check_database", lambda: True)
    response = client.get("/health")
    assert response["X-Request-ID"]


@pytest.mark.parametrize("sslmode", [None, "verify-full", "disable"])
def test_production_database_tls_defaults_without_mutating_base(monkeypatch, sslmode):
    options = {} if sslmode is None else {"sslmode": sslmode}
    original = {"default": {"OPTIONS": options}}
    monkeypatch.setattr(base, "DATABASES", original)
    configured = runpy.run_path(
        str(base.BASE_DIR / "config/settings/prod.py"),
        run_name="config.settings._review_prod",
    )
    assert configured["DATABASES"]["default"]["OPTIONS"]["sslmode"] == (
        sslmode or "require"
    )
    assert original["default"]["OPTIONS"] == options
    assert ("sslmode" in options) == (sslmode is not None)


@pytest.mark.parametrize(
    "message",
    [
        "password=HiddenCredential",
        '"password": "HiddenCredential with spaces"',
        "Authorization: Bearer HiddenCredential",
    ],
)
def test_log_credential_values_are_removed(message):
    record = logging.LogRecord(
        "app.operation", logging.WARNING, __file__, 1, message, (), None
    )
    assert "HiddenCredential" not in SafeJsonFormatter().format(record)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "language,title",
    [
        ("en", "Access denied"),
        ("ur", "رسائی کی اجازت نہیں"),
    ],
)
def test_csrf_failure_is_generic_localized_and_has_no_inline_content(language, title):
    from django.test import Client

    response = Client(enforce_csrf_checks=True).post(f"/{language}/accounts/login/", {})
    assert response.status_code == 403
    assert title in response.text
    assert "CSRF cookie not set" not in response.text
    assert "<style" not in response.text
    assert "style=" not in response.text
    assert "Content-Security-Policy" in response
