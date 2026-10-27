import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import polib
import pytest
from django.core.cache import cache
from django.db import connections
from django.test import RequestFactory, override_settings

from apps.accounts import services
from apps.audit.models import AuditLog

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def login_clock_and_cache(clock, db):
    cache.clear()


def attempt(client, number, **headers):
    return client.post(
        "/en/accounts/login/",
        {"email": f"unknown{number}@example.com", "password": "invalid"},
        **headers,
    )


def test_login_twenty_first_post_across_emails_is_limited(client):
    for number in range(20):
        response = attempt(
            client,
            number,
            HTTP_X_FORWARDED_FOR=f"198.51.100.{number}, 203.0.113.42",
        )
        assert response.status_code == 200
    response = attempt(client, 20, HTTP_X_FORWARDED_FOR="203.0.113.42")
    assert response.status_code == 429
    assert "Too many login attempts" in response.text
    event = AuditLog.objects.get(action="auth.rate_limited")
    assert event.actor is None and event.actor_label == "anonymous"
    assert event.ip == "203.0.113.42"
    assert event.metadata == {"reason": "client_ip_limit"}
    assert not event.before and not event.after
    assert "unknown" not in json.dumps(event.metadata)
    assert "invalid" not in response.text
    assert AuditLog.objects.filter(action="auth.login_failed").count() == 20
    assert attempt(client, 21, HTTP_X_FORWARDED_FOR="203.0.113.43").status_code == 200


@pytest.mark.parametrize("rule", ["login_rate_per_minute", "login_rate_per_day"])
def test_login_limits_read_business_rules(client, settings, rule):
    settings.BUSINESS_RULES = {**settings.BUSINESS_RULES, rule: 2}
    for number in range(2):
        assert attempt(client, number).status_code == 200
    assert attempt(client, 2).status_code == 429


def test_get_does_not_consume_login_limit(client, settings):
    settings.BUSINESS_RULES = {
        **settings.BUSINESS_RULES,
        "login_rate_per_minute": 1,
    }
    for _ in range(3):
        assert client.get("/en/accounts/login/").status_code == 200
    assert attempt(client, 1).status_code == 200
    assert attempt(client, 2).status_code == 429


def test_login_limit_resets_next_day(client, settings, clock):
    settings.BUSINESS_RULES = {**settings.BUSINESS_RULES, "login_rate_per_day": 1}
    assert attempt(client, 1).status_code == 200
    assert attempt(client, 2).status_code == 429
    clock.shift(86400)
    assert attempt(client, 3).status_code == 200


def test_login_rate_page_is_translated(client, settings, tmp_path):
    catalogue = tmp_path / "ur" / "LC_MESSAGES"
    catalogue.mkdir(parents=True)
    polib.pofile(
        str(settings.BASE_DIR / "locale" / "ur" / "LC_MESSAGES" / "django.po")
    ).save_as_mofile(str(catalogue / "django.mo"))
    settings.BUSINESS_RULES = {
        **settings.BUSINESS_RULES,
        "login_rate_per_minute": 1,
    }
    with override_settings(LOCALE_PATHS=[tmp_path]):
        client.post("/ur/accounts/login/", {})
        response = client.post("/ur/accounts/login/", {})
    assert response.status_code == 429
    assert "اس کنکشن سے لاگ ان کی بہت زیادہ کوششیں" in response.text


@pytest.mark.django_db(transaction=True)
def test_login_counter_is_atomic_across_workers(settings):
    settings.BUSINESS_RULES = {
        **settings.BUSINESS_RULES,
        "login_rate_per_minute": 2,
    }
    barrier = Barrier(3)

    def check():
        try:
            request = RequestFactory().post("/en/accounts/login/")
            barrier.wait(timeout=10)
            return services.login_rate_limited(request)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(lambda _: check(), range(3)))
    assert sorted(results) == [False, False, True]
    assert AuditLog.objects.filter(action="auth.rate_limited").count() == 1
