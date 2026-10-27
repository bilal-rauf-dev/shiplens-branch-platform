import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from threading import Barrier
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import polib
import pytest
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import connections
from django.test import Client, RequestFactory
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.branches.models import BranchStatus
from apps.core import clock as business_clock
from apps.core.models import IdSequence
from apps.volunteers import services
from apps.volunteers.forms import ApplicationForm
from apps.volunteers.models import Application, ApplicationStatus, MemberStatus

pytestmark = pytest.mark.django_db


def test_t_app_submit_ok_and_consent(client, post_data, settings):
    response = client.post(
        reverse("volunteer-apply"), post_data, HTTP_X_FORWARDED_FOR="203.0.113.12"
    )
    assert response.status_code == 302
    application = Application.objects.get()
    assert application.reference == "APP-2026-00001"
    assert (
        application.email == "ayesha@example.com"
        and application.phone == "+923001234567"
    )
    assert application.status == ApplicationStatus.PENDING
    assert application.consent_at == business_clock.now()
    assert (
        application.ip_hash
        == hashlib.sha256(("203.0.113.12" + settings.SECRET_KEY).encode()).hexdigest()
    )
    assert parse_qs(urlsplit(response.url).query) == {"ref": [application.reference]}
    event = AuditLog.objects.get(action="application.submitted")
    assert event.actor is None and event.actor_label == "anonymous"
    assert event.after == {
        "reference": application.reference,
        "preferred_branch_id": application.preferred_branch_id,
    }
    assert event.ip is None and event.user_agent == ""
    serialized = json.dumps(event.after | event.before | event.metadata)
    for pii in (
        application.full_name,
        application.email,
        application.phone,
        "2000-01-01",
    ):
        assert pii not in serialized
    thanks = client.get(response.url)
    assert thanks.status_code == 200
    assert (
        application.full_name not in thanks.text
        and application.email not in thanks.text
    )


def test_t_app_spam_honeypot(client, post_data):
    response = client.post(
        reverse("volunteer-apply"), {**post_data, "website": "https://spam.example"}
    )
    assert response.status_code == 302
    assert not Application.objects.exists()
    assert re.fullmatch(
        r"APP-2026-[0-9]{5}", parse_qs(urlsplit(response.url).query)["ref"][0]
    )
    event = AuditLog.objects.get(action="application.spam_blocked")
    assert event.metadata == {"reason": "honeypot"}
    assert not event.after and not event.before and event.ip is None


@pytest.mark.parametrize(
    "failure", ["fast", "expired", "tampered", "missing", "bad-payload", "future"]
)
def test_t_app_spam_timing(client, valid_data, clock, failure):
    payload = valid_data.copy()
    if failure == "expired":
        clock.shift(7201)
    elif failure == "tampered":
        payload["render_token"] += "tampered"
    elif failure == "missing":
        payload.pop("render_token")
    elif failure == "bad-payload":
        payload["render_token"] = signing.dumps(
            {"rendered_at": "invalid"}, salt="apply-form"
        )
    elif failure == "future":
        payload["render_token"] = signing.dumps(
            {"rendered_at": business_clock.now().timestamp() + 60}, salt="apply-form"
        )
    response = client.post(reverse("volunteer-apply"), payload)
    assert response.status_code == 302
    assert not Application.objects.exists()
    assert AuditLog.objects.get(action="application.spam_blocked").metadata == {
        "reason": "timing"
    }


def test_t_app_spam_rate(client, post_data):
    for _ in range(5):
        assert client.post(reverse("volunteer-apply"), post_data).status_code == 302
    sixth = client.post(reverse("volunteer-apply"), post_data)
    assert sixth.status_code == 429
    assert "Please try again later" in sixth.text
    assert Application.objects.count() == 5


def test_daily_rate_limit(client, post_data, settings):
    settings.BUSINESS_RULES = {**settings.BUSINESS_RULES, "apply_rate_per_hour": 50}
    for _ in range(20):
        assert client.post(reverse("volunteer-apply"), post_data).status_code == 302
    assert client.post(reverse("volunteer-apply"), post_data).status_code == 429


def test_t_app_dup_flag_and_no_enum(client, post_data):
    fresh = client.post(reverse("volunteer-apply"), post_data)
    duplicate = client.post(reverse("volunteer-apply"), post_data)
    first, second = Application.objects.order_by("pk")
    assert not first.possible_duplicate
    assert second.possible_duplicate and second.duplicate_of_application_id == first.pk
    assert fresh.status_code == duplicate.status_code == 302
    assert urlsplit(fresh.url).path == urlsplit(duplicate.url).path
    first_page, second_page = client.get(fresh.url), client.get(duplicate.url)
    assert first_page.templates[0].name == second_page.templates[0].name
    assert first_page.text.replace(
        first.reference, "REFERENCE"
    ) == second_page.text.replace(second.reference, "REFERENCE")
    assert "duplicate" not in second_page.text.lower()


@pytest.mark.parametrize(
    "status,expected",
    [
        (MemberStatus.ACTIVE, True),
        (MemberStatus.INACTIVE, True),
        (MemberStatus.LEFT, False),
    ],
)
def test_t_app_dup_flag_member(client, post_data, member_factory, status, expected):
    member = member_factory(
        email="ayesha@example.com",
        status=status,
        left_on="2026-10-25" if status == MemberStatus.LEFT else None,
    )
    assert client.post(reverse("volunteer-apply"), post_data).status_code == 302
    application = Application.objects.get()
    assert application.possible_duplicate == expected
    assert application.duplicate_of_member_id == (member.pk if expected else None)


def test_service_rechecks_branch_and_consent(valid_data, branch):
    form = ApplicationForm(valid_data)
    assert form.is_valid()
    branch.status = BranchStatus.PAUSED
    branch.save(update_fields=["status"])
    with pytest.raises(ValidationError):
        services.submit_application(form.cleaned_data, "203.0.113.1")
    assert not Application.objects.exists()
    assert not IdSequence.objects.filter(pk="application:2026").exists()
    with pytest.raises(ValidationError):
        services.submit_application(
            {**form.cleaned_data, "privacy_consent": False}, None
        )


def test_audit_failure_rolls_back_submission_and_counter(valid_data):
    form = ApplicationForm(valid_data)
    assert form.is_valid()
    with patch(
        "apps.volunteers.services.audit.record",
        side_effect=RuntimeError("audit unavailable"),
    ):
        with pytest.raises(RuntimeError):
            services.submit_application(form.cleaned_data, None)
    assert not Application.objects.exists()
    assert not IdSequence.objects.filter(pk="application:2026").exists()


def test_public_form_retains_csrf_protection(post_data):
    client = Client(enforce_csrf_checks=True)
    assert client.post(reverse("volunteer-apply"), post_data).status_code == 403
    assert not Application.objects.exists()


def test_thanks_has_no_lookup_or_pii_reflection(client):
    assert (
        "<script>"
        not in client.get(reverse("volunteer-thanks"), {"ref": "<script>"}).text
    )
    assert (
        client.get(reverse("volunteer-thanks"), {"ref": "APP-2026-99999"}).status_code
        == 200
    )


class FormMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inputs = []
        self.labels = set()
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "label":
            self.labels.add(attrs.get("for"))
        if tag in {"input", "select", "textarea"}:
            self.inputs.append(attrs)


def test_form_accessibility_and_error_links(client, post_data):
    response = client.post(
        reverse("volunteer-apply"), {**post_data, "full_name": "Al", "interests": []}
    )
    assert response.status_code == 200
    markup = FormMarkup()
    markup.feed(response.text)
    for field in markup.inputs:
        if field.get("type") != "hidden":
            assert field["id"] in markup.labels
        if field.get("name") == "full_name":
            assert field["aria-invalid"] == "true"
            assert all(
                value in markup.ids for value in field["aria-describedby"].split()
            )
    assert 'href="#id_full_name"' in response.text
    assert "<fieldset" in response.text and "<legend" in response.text
    assert 'class="honeypot" aria-hidden="true"' in response.text
    assert "<script" not in response.text


def test_urdu_form_defaults_to_urdu(client):
    response = client.get("/ur/get-involved/")
    assert response.status_code == 200
    assert response.context["form"].initial["preferred_language"] == "ur"


def test_urdu_public_form_and_rate_message(client, settings, tmp_path, monkeypatch):
    source = settings.BASE_DIR / "locale" / "ur" / "LC_MESSAGES" / "django.po"
    compiled = tmp_path / "ur" / "LC_MESSAGES" / "django.mo"
    compiled.parent.mkdir(parents=True)
    polib.pofile(str(source)).save_as_mofile(str(compiled))
    settings.LOCALE_PATHS = [tmp_path]
    page = client.get("/ur/get-involved/")
    assert page.status_code == 200 and 'dir="rtl"' in page.text
    assert "رضاکار بنیں" in page.text
    monkeypatch.setattr(services, "application_rate_limited", lambda request: True)
    limited = client.post("/ur/get-involved/")
    assert limited.status_code == 429
    assert "بہت زیادہ درخواستیں" in limited.text


def test_branch_changed_after_form_validation_is_reported_inline(
    client, post_data, branch, monkeypatch
):
    submit = services.submit_application

    def pause_then_submit(cleaned, ip):
        branch.status = BranchStatus.PAUSED
        branch.save(update_fields=["status"])
        return submit(cleaned, ip)

    monkeypatch.setattr(services, "submit_application", pause_then_submit)
    response = client.post(reverse("volunteer-apply"), post_data)
    assert response.status_code == 200
    assert "This branch is not accepting applications." in response.text
    assert not Application.objects.exists()


def test_submission_audit_is_anonymous_for_signed_in_visitors(client, admin, post_data):
    client.force_login(admin, backend="apps.accounts.backends.EmailBackend")
    assert client.post(reverse("volunteer-apply"), post_data).status_code == 302
    event = AuditLog.objects.get(action="application.submitted")
    assert event.actor_id is None and event.actor_label == "anonymous"


@pytest.mark.django_db(transaction=True)
def test_rate_limit_is_atomic_between_workers():
    barrier = Barrier(6)

    def check(index):
        try:
            request = RequestFactory().post(
                "/en/get-involved/", REMOTE_ADDR="203.0.113.80"
            )
            barrier.wait(timeout=20)
            return services.application_rate_limited(request)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(check, range(6)))
    assert results.count(False) == 5 and results.count(True) == 1
