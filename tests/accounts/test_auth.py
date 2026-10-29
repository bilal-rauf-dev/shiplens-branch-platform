from datetime import timedelta

import pytest
from axes.models import AccessAttempt
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.password_validation import validate_password
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client

from apps.accounts import services
from apps.accounts.models import Role, User
from apps.core import clock as business_clock
from tests.accounts.conftest import TEST_PASSWORD

NEW_PASSWORD = "Cobalt!Harbor-83-Pine"  # noqa: S105 -- test-only credential.


@pytest.mark.parametrize(
    "role,path",
    [
        (Role.SUPER_ADMIN, "/ur/app/dashboard/"),
        (Role.FINANCE_REVIEWER, "/ur/app/dashboard/"),
        (Role.BRANCH_LEAD, "/ur/app/my-branch/"),
        (Role.HR_LEAD, "/ur/app/hr/"),
        (Role.CONTENT_EDITOR, "/ur/app/content/"),
    ],
)
@pytest.mark.django_db
def test_t_auth_login(client, role, path, clock):
    user = User.objects.create_user(
        email="MixedCase@example.com",
        full_name="Local Operator",
        role=role,
        password=TEST_PASSWORD,
    )

    response = client.post(
        "/ur/accounts/login/",
        {"email": "MIXEDCASE@EXAMPLE.COM", "password": TEST_PASSWORD},
    )

    assert response.status_code == 302
    assert response.url == path
    assert client.session[SESSION_KEY] == str(user.pk)
    page = client.get(path)
    assert page.status_code == 200
    assert '<html lang="ur" dir="rtl">' in page.text


@pytest.mark.parametrize("account", ["unknown", "wrong_password", "inactive"])
def test_t_auth_login_generic_error(client, user, account, clock):
    email, password = user.email, TEST_PASSWORD
    if account == "unknown":
        email = "unknown@example.com"
    elif account == "inactive":
        User.objects.filter(pk=user.pk).update(is_active=False)
    else:
        password = "Incorrect-password-19!"  # noqa: S105 -- invalid test credential.

    response = client.post(
        "/en/accounts/login/", {"email": email, "password": password}
    )

    assert response.status_code == 200
    assert "Email or password is incorrect." in response.text
    assert SESSION_KEY not in client.session


def test_t_sec_lockout(client, user, clock):
    for attempt in range(5):
        response = client.post(
            "/en/accounts/login/",
            {
                "email": user.email.upper(),
                "password": "Incorrect-password-19!",
            },
            HTTP_X_FORWARDED_FOR=f"198.51.100.{attempt}, 203.0.113.9",
        )
        assert response.status_code == (200 if attempt < 4 else 429)

    response = client.post(
        "/en/accounts/login/",
        {
            "email": user.email,
            "password": TEST_PASSWORD,
        },
        HTTP_X_FORWARDED_FOR="192.0.2.250, 203.0.113.9",
    )

    assert response.status_code == 429
    assert "Too many attempts. Try again in 15 minutes." in response.text
    assert SESSION_KEY not in client.session
    attempt = AccessAttempt.objects.get(username=user.email)
    assert attempt.ip_address == "203.0.113.9"
    assert attempt.failures_since_start == 5

    clock.shift(timedelta(minutes=14, seconds=59))
    assert (
        client.post(
            "/en/accounts/login/",
            {"email": user.email, "password": TEST_PASSWORD},
            HTTP_X_FORWARDED_FOR="192.0.2.250, 203.0.113.9",
        ).status_code
        == 429
    )
    clock.shift(timedelta(seconds=2))
    response = client.post(
        "/en/accounts/login/",
        {
            "email": user.email,
            "password": TEST_PASSWORD,
        },
        HTTP_X_FORWARDED_FOR="192.0.2.250, 203.0.113.9",
    )
    assert response.status_code == 302


def test_t_auth_force_change(client, user, clock):
    User.objects.filter(pk=user.pk).update(must_change_password=True)
    response = client.post(
        "/en/accounts/login/", {"email": user.email, "password": TEST_PASSWORD}
    )
    assert response.url == "/en/accounts/change-password/"

    blocked = client.get("/en/app/dashboard/")
    assert blocked.status_code == 302
    assert blocked.url == "/en/accounts/change-password/"
    assert client.get("/en/accounts/change-password/").status_code == 200
    assert client.get("/en/accounts/logout/").status_code == 405
    assert client.get("/health").status_code == 200

    previous_key = client.session.session_key
    response = client.post(
        "/en/accounts/change-password/",
        {
            "old_password": TEST_PASSWORD,
            "new_password1": NEW_PASSWORD,
            "new_password2": NEW_PASSWORD,
        },
    )

    assert response.status_code == 302
    assert response.url == "/en/app/dashboard/"
    user.refresh_from_db()
    assert user.must_change_password is False
    assert user.check_password(NEW_PASSWORD)
    assert not user.check_password(TEST_PASSWORD)
    assert client.session.session_key != previous_key
    assert client.get("/en/app/dashboard/").status_code == 200


@pytest.mark.parametrize(
    "password,code",
    [
        ("tiny", "password_too_short"),
        ("password123", "password_too_common"),
        ("4820951837489321", "password_entirely_numeric"),
        ("operator@example.com", "password_too_similar"),
    ],
)
def test_t_sec_password(user, password, code):
    with pytest.raises(ValidationError) as raised:
        validate_password(password, user=user)
    assert code in [error.code for error in raised.value.error_list]


def test_t_sec_password_hash(user):
    assert user.password.startswith("argon2$")
    assert user.check_password(TEST_PASSWORD)
    assert not hasattr(user, "is_staff")
    assert not hasattr(user, "is_superuser")


def test_t_sec_session_rotate(client, user, clock):
    session = client.session
    session["before_login"] = True
    session.save()
    previous_key = session.session_key

    response = client.post(
        "/en/accounts/login/", {"email": user.email, "password": TEST_PASSWORD}
    )

    assert response.status_code == 302
    assert client.session.session_key != previous_key
    assert not Session.objects.filter(session_key=previous_key).exists()


def test_session_idle_timeout(signed_in, clock):
    clock.shift(timedelta(minutes=59))
    assert signed_in.get("/en/app/dashboard/").status_code == 200
    clock.shift(timedelta(hours=1))

    response = signed_in.get("/en/app/dashboard/")

    assert response.status_code == 302
    assert response.url.startswith("/en/accounts/login/")
    assert SESSION_KEY not in signed_in.session


def test_session_absolute_timeout_does_not_slide(signed_in, clock):
    expiry = signed_in.session.get_expiry_date()
    assert expiry == business_clock.now() + timedelta(hours=8)
    for _ in range(15):
        clock.shift(timedelta(minutes=30))
        assert signed_in.get("/en/app/dashboard/").status_code == 200
        assert signed_in.session.get_expiry_date() == expiry
    clock.shift(timedelta(minutes=30))

    response = signed_in.get("/en/app/dashboard/")

    assert response.status_code == 302
    assert SESSION_KEY not in signed_in.session


def test_logout_get_is_405_and_post_flushes_session(signed_in):
    assert signed_in.get("/en/accounts/logout/").status_code == 405
    assert SESSION_KEY in signed_in.session

    response = signed_in.post("/en/accounts/logout/")

    assert response.status_code == 302
    assert SESSION_KEY not in signed_in.session


def test_t_sec_csrf_login_and_logout(user, clock):
    client = Client(enforce_csrf_checks=True)
    assert (
        client.post(
            "/en/accounts/login/", {"email": user.email, "password": TEST_PASSWORD}
        ).status_code
        == 403
    )
    client.get("/en/accounts/login/")
    token = client.cookies["csrftoken"].value
    assert (
        client.post(
            "/en/accounts/login/",
            {
                "email": user.email,
                "password": TEST_PASSWORD,
                "csrfmiddlewaretoken": token,
            },
        ).status_code
        == 302
    )
    assert client.post("/en/accounts/logout/").status_code == 403


def test_placeholder_rejects_wrong_role_and_anonymous(client, signed_in):
    assert signed_in.get("/en/app/my-branch/").status_code == 403
    anonymous = Client()
    assert anonymous.get("/en/app/content/").status_code == 302
    assert anonymous.get("/en/accounts/change-password/").status_code == 302


def test_login_ignores_external_next_and_redirects_existing_user(signed_in):
    response = signed_in.get("/en/accounts/login/?next=https://untrusted.example/")
    assert response.status_code == 302
    assert response.url == "/en/app/dashboard/"


def test_user_email_unique_ignoring_case(user):
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create(
            [
                User(
                    email=user.email.upper(),
                    full_name="Another Operator",
                    role=Role.HR_LEAD,
                    password="!",  # noqa: S106 -- unusable password sentinel.
                )
            ]
        )


@pytest.mark.parametrize(
    "field,value", [("role", "UNKNOWN"), ("preferred_language", "xx")]
)
def test_user_database_checks(user, field, value):
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=user.pk).update(**{field: value})


def test_password_service_rechecks_old_password(signed_in, user, rf):
    request = rf.post("/en/accounts/change-password/")
    request.user = user
    request.session = signed_in.session
    with pytest.raises(ValidationError):
        services.change_password(request, "Incorrect-password-19!", NEW_PASSWORD)
    user.refresh_from_db()
    assert user.check_password(TEST_PASSWORD)


def test_demo_password_change_blocked(signed_in, user):
    User.objects.filter(pk=user.pk).update(is_demo=True)
    response = signed_in.post(
        "/en/accounts/change-password/",
        {
            "old_password": TEST_PASSWORD,
            "new_password1": NEW_PASSWORD,
            "new_password2": NEW_PASSWORD,
        },
    )
    assert response.status_code == 403
    user.refresh_from_db()
    assert user.check_password(TEST_PASSWORD)


def test_t_log_no_pii_in_failed_login(client, user, caplog, clock):
    client.post(
        "/en/accounts/login/",
        {"email": user.email, "password": "Incorrect-password-19!"},
    )
    assert user.email not in caplog.text
    assert "Incorrect-password-19!" not in caplog.text


@pytest.mark.parametrize("password", ["tiny", "password123"])
def test_change_password_rejects_short_and_common_values(signed_in, user, password):
    original_hash = user.password

    response = signed_in.post(
        "/en/accounts/change-password/",
        {
            "old_password": TEST_PASSWORD,
            "new_password1": password,
            "new_password2": password,
        },
    )

    assert response.status_code == 200
    assert "new_password2" in response.context["form"].errors
    user.refresh_from_db()
    assert user.password == original_hash


@pytest.mark.django_db
def test_user_manager_bootstrap_super_admin():
    user = User.objects.create_superuser(
        email="ADMIN@example.com",
        full_name="Bootstrap Operator",
        password=TEST_PASSWORD,
    )

    assert user.email == "admin@example.com"
    assert user.role == Role.SUPER_ADMIN
    assert user.is_active
    assert User.objects.get_by_natural_key("ADMIN@EXAMPLE.COM") == user
    with pytest.raises(ValueError):
        User.objects.create_superuser(
            email="other@example.com",
            full_name="Other Operator",
            role=Role.FINANCE_REVIEWER,
            password=TEST_PASSWORD,
        )
    with pytest.raises(ValueError):
        User.objects.create_user("", full_name="No Email", role=Role.HR_LEAD)
