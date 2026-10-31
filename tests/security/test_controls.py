from datetime import timedelta
from html import escape

import pytest
from django.test import Client, override_settings

from apps.accounts.models import User
from apps.core import rules
from apps.volunteers.models import Application
from config.settings import prod
from tests.accounts.conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db
POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
    "frame-ancestors 'none'; form-action 'self'; base-uri 'self'; object-src 'none'"
)


@pytest.fixture
def staff(client, sample_data):
    client.force_login(User.objects.get(role="SUPER_ADMIN"))
    return client


@pytest.mark.parametrize("path", ["/en/", "/en/app/dashboard/", "/health"])
def test_t_sec_headers(staff, path):
    response = staff.get(path)
    assert response.status_code == 200
    # django-csp serializes directives in arbitrary order. Compare the exact policy,
    # permitting only directive ordering to differ, never sources or directives.
    assert set(response["Content-Security-Policy"].split("; ")) == set(
        POLICY.split("; ")
    )
    assert "Content-Security-Policy-Report-Only" not in response
    assert response["Permissions-Policy"] == (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    )
    assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"


def test_t_sec_cookies(clock):
    names = (
        "SESSION_COOKIE_NAME",
        "SESSION_COOKIE_SECURE",
        "SESSION_COOKIE_HTTPONLY",
        "SESSION_COOKIE_SAMESITE",
        "SESSION_COOKIE_PATH",
        "SESSION_COOKIE_DOMAIN",
        "CSRF_COOKIE_NAME",
        "CSRF_COOKIE_SECURE",
        "CSRF_COOKIE_HTTPONLY",
        "CSRF_COOKIE_SAMESITE",
        "CSRF_COOKIE_PATH",
        "CSRF_COOKIE_DOMAIN",
    )
    User.objects.create_user(
        email="cookie@example.com",
        password=TEST_PASSWORD,
        full_name="Cookie User",
        role="SUPER_ADMIN",
    )
    with override_settings(
        **{name: getattr(prod, name) for name in names}, SECURE_SSL_REDIRECT=True
    ):
        client = Client(enforce_csrf_checks=True)
        client.get("/en/accounts/login/", secure=True)
        response = client.post(
            "/en/accounts/login/",
            {
                "email": "cookie@example.com",
                "password": TEST_PASSWORD,
                "csrfmiddlewaretoken": client.cookies["__Host-csrftoken"].value,
            },
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )
        assert response.status_code == 302
        for name in ("__Host-sid", "__Host-csrftoken"):
            cookie = response.cookies[name]
            assert cookie["secure"] and cookie["httponly"]
            assert cookie["samesite"] == "Lax"
            assert cookie["path"] == "/" and not cookie["domain"]


@pytest.mark.parametrize(
    "path", ["/en/accounts/login/", "/en/get-involved/", "/en/app/settings/update/"]
)
def test_t_sec_csrf(sample_data, path):
    client = Client(enforce_csrf_checks=True)
    if "/app/" in path:
        client.force_login(User.objects.get(role="SUPER_ADMIN"))
    assert client.post(path, {}).status_code == 403


@pytest.mark.parametrize(
    "path,status,title",
    [
        ("registry/denied/", 403, "رسائی کی اجازت نہیں"),
        ("missing-private-record/", 404, "صفحہ نہیں ملا"),
        ("registry/crash/", 500, "کچھ غلط ہو گیا"),
    ],
)
def test_t_sec_errors(staff, test_routes, error_catalog, settings, path, status, title):
    settings.DEBUG = False
    staff.raise_request_exception = False
    response = staff.get(f"/ur/{path}")
    assert response.status_code == status
    assert title in response.text and 'lang="ur" dir="rtl"' in response.text
    for secret in (
        "Traceback",
        "private database details",
        "private entity details",
        "missing-private-record",
        "RuntimeError",
        "PermissionDenied",
    ):
        assert secret not in response.text


def test_t_sec_sqli(staff):
    response = staff.get("/en/app/members/", {"q": "' OR 1=1 --"})
    assert response.status_code == 200
    assert list(response.context["members"]) == []
    assert staff.get("/en/app/members/").context["paginator"].count == 9


def test_t_sec_xss_reflect(staff):
    value = '<script>alert("reflected")</script>'
    response = staff.get("/en/app/members/", {"q": value})
    assert response.status_code == 200
    assert value not in response.text
    assert escape(value, quote=True) in response.text


def test_t_log_no_pii(client, sample_data, clock, caplog):
    caplog.clear()
    email, phone, password = (
        "private-probe@example.com",
        "+923001112233",
        "SecretProbe!8724",
    )
    response = client.post(
        "/en/accounts/login/", {"email": email, "password": password}
    )
    assert response.status_code == 200
    form = client.get("/en/get-involved/").context["form"]
    clock.shift(timedelta(seconds=rules.get("form_min_seconds")))
    branch = form.fields["preferred_branch"].queryset.first()
    response = client.post(
        "/en/get-involved/",
        {
            "full_name": "Privacy Probe",
            "email": email,
            "phone": phone,
            "date_of_birth": "2000-01-01",
            "preferred_branch": branch.pk,
            "interests": ["education"],
            "availability": ["weekends"],
            "motivation": "I would like to help my local community as a volunteer.",
            "preferred_language": "en",
            "privacy_consent": True,
            "render_token": form.initial["render_token"],
        },
    )
    assert response.status_code == 302
    assert Application.objects.filter(email=email).exists()
    messages = "\n".join(record.getMessage() for record in caplog.records)
    for private in (email, phone, phone[3:], password):
        assert private not in messages
