from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch

import polib
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connections
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Role, User, UserBranchAssignment
from apps.accounts.services import assign_branch
from apps.audit.models import AuditLog
from apps.branches import services
from apps.branches.models import Branch, BranchStatus
from apps.core import clock as business_clock

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return User.objects.create_user(
        email="lifecycle@example.com",
        full_name="Lifecycle Admin",
        role=Role.SUPER_ADMIN,
    )


@pytest.fixture
def branch(branch_factory, admin):
    return branch_factory(created_by=admin, updated_by=admin)


@pytest.fixture
def signed_in(client, admin, clock):
    client.force_login(admin, backend="apps.accounts.backends.EmailBackend")
    return client


def endpoint(branch, action):
    return reverse("branch-transition", kwargs={"pk": branch.pk, "action": action})


EXPECTED = {
    ("FORMING", "activate"): ("ACTIVE", "branch.activated"),
    ("ACTIVE", "pause"): ("PAUSED", "branch.paused"),
    ("PAUSED", "resume"): ("ACTIVE", "branch.resumed"),
    ("FORMING", "close"): ("CLOSED", "branch.closed"),
    ("ACTIVE", "close"): ("CLOSED", "branch.closed"),
    ("PAUSED", "close"): ("CLOSED", "branch.closed"),
}


@pytest.mark.parametrize("status", BranchStatus.values)
@pytest.mark.parametrize("action", ["activate", "pause", "resume", "close"])
def test_t_brn_transitions(admin, branch, status, action, clock):
    Branch.objects.filter(pk=branch.pk).update(status=status)
    before = Branch.objects.values().get(pk=branch.pk)
    expected = EXPECTED.get((status, action))
    if expected is None:
        with pytest.raises(services.InvalidTransition):
            services.transition(admin, branch, action, "A useful reason")
        assert Branch.objects.values().get(pk=branch.pk) == before
        assert not AuditLog.objects.exists()
    else:
        changed = services.transition(admin, branch, action, "A useful reason")
        assert changed.status == expected[0]
        assert changed.updated_by == admin
        assert changed.updated_at == business_clock.now()
        event = AuditLog.objects.get(action=expected[1])
        assert event.before["status"] == status
        assert event.after["status"] == expected[0]
        assert event.branch_id == branch.pk
        assert changed.status_reason == (
            "A useful reason" if action in {"pause", "close"} else ""
        )


def test_opened_and_closed_dates_follow_karachi_clock(admin, branch, clock):
    # Midnight Karachi still falls on the previous UTC day.
    clock.move_to("2026-10-26T00:05:00+05:00")
    active = services.transition(admin, branch, "activate")
    assert active.opened_on == date(2026, 10, 26)
    clock.shift(86400)
    services.transition(admin, branch, "pause", "Maintenance")
    clock.shift(86400)
    resumed = services.transition(admin, branch, "resume")
    assert resumed.opened_on == active.opened_on
    assert resumed.status_reason == ""
    clock.shift(86400)
    closed = services.transition(admin, branch, "close", "Work completed")
    assert closed.opened_on == active.opened_on
    assert closed.closed_on == date(2026, 10, 29)
    event = AuditLog.objects.get(action="branch.closed")
    assert event.after["closed_on"] == "2026-10-29"


def test_first_activation_keeps_existing_opened_date(admin, branch, clock):
    Branch.objects.filter(pk=branch.pk).update(opened_on=date(2026, 10, 1))
    assert services.transition(admin, branch, "activate").opened_on == date(2026, 10, 1)


def test_close_forming_has_no_opened_date(admin, branch, clock):
    closed = services.transition(admin, branch, "close", "Plans cancelled")
    assert closed.opened_on is None
    assert closed.closed_on == business_clock.today()


@pytest.mark.parametrize("action,status", [("pause", "ACTIVE"), ("close", "FORMING")])
@pytest.mark.parametrize("reason", ["", "     ", "abcd", "x" * 301])
def test_reason_validation(admin, branch, action, status, reason):
    Branch.objects.filter(pk=branch.pk).update(status=status)
    before = Branch.objects.values().get(pk=branch.pk)
    with pytest.raises(ValidationError):
        services.transition(admin, branch, action, reason)
    assert Branch.objects.values().get(pk=branch.pk) == before
    assert not AuditLog.objects.exists()


@pytest.mark.parametrize("reason", ["12345", "x" * 300])
def test_reason_accepts_boundaries_and_trims(admin, branch, reason):
    changed = services.transition(admin, branch, "close", f"  {reason}  ")
    assert changed.status_reason == reason


def test_reason_limits_come_from_rules(admin, branch, settings):
    settings.BUSINESS_RULES = {
        **settings.BUSINESS_RULES,
        "branch_reason_min_length": 8,
        "branch_reason_max_length": 10,
    }
    with pytest.raises(ValidationError):
        services.transition(admin, branch, "close", "1234567")
    with pytest.raises(ValidationError):
        services.transition(admin, branch, "close", "12345678901")
    assert (
        services.transition(admin, branch, "close", "12345678").status
        == BranchStatus.CLOSED
    )


def test_t_brn_close_guard_returns_409_and_preserves_branch(
    signed_in, branch, monkeypatch
):
    monkeypatch.setattr(
        services, "close_blockers", lambda row: ["Unsent collections", "Open reports"]
    )
    before = Branch.objects.values().get(pk=branch.pk)
    response = signed_in.post(endpoint(branch, "close"), {"reason": "Ready to close"})
    assert response.status_code == 409
    assert "Unsent collections; Open reports" in response.text
    assert Branch.objects.values().get(pk=branch.pk) == before
    assert not AuditLog.objects.filter(action="branch.closed").exists()


def test_view_conflicts_validation_and_methods(signed_in, branch):
    assert signed_in.get(endpoint(branch, "activate")).status_code == 405
    assert signed_in.post(endpoint(branch, "unknown")).status_code == 409
    assert (
        signed_in.post(endpoint(branch, "close"), {"reason": "bad"}).status_code == 400
    )
    assert signed_in.post(endpoint(branch, "activate")).status_code == 302
    assert signed_in.post(endpoint(branch, "activate")).status_code == 409
    assert AuditLog.objects.filter(action="branch.activated").count() == 1
    missing = reverse(
        "branch-transition", kwargs={"pk": branch.pk + 999, "action": "activate"}
    )
    assert signed_in.post(missing).status_code == 404


def test_transition_keeps_csrf_protection(admin, branch):
    client = Client(enforce_csrf_checks=True)
    client.force_login(admin, backend="apps.accounts.backends.EmailBackend")
    assert client.post(endpoint(branch, "activate")).status_code == 403
    branch.refresh_from_db()
    assert branch.status == BranchStatus.FORMING


def test_transition_responses_are_translated(
    signed_in, branch, settings, tmp_path, monkeypatch
):
    source = settings.BASE_DIR / "locale" / "ur" / "LC_MESSAGES" / "django.po"
    compiled = tmp_path / "ur" / "LC_MESSAGES" / "django.mo"
    compiled.parent.mkdir(parents=True)
    polib.pofile(str(source)).save_as_mofile(str(compiled))
    settings.LOCALE_PATHS = [tmp_path]
    root = f"/ur/branches/{branch.pk}"
    blocked = signed_in.post(f"{root}/resume/")
    assert blocked.status_code == 409
    assert "شاخ کی موجودہ حالت" in blocked.text
    monkeypatch.setattr(services, "close_blockers", lambda row: ["باقی کام"])
    blocked_close = signed_in.post(f"{root}/close/", {"reason": "Ready to close"})
    assert blocked_close.status_code == 409
    assert "یہ شاخ بند نہیں کی جا سکتی" in blocked_close.text
    invalid = signed_in.post(f"{root}/close/", {"reason": "bad"})
    assert invalid.status_code == 400
    assert "حروف میں وجہ لکھیں" in invalid.text
    success = signed_in.post(f"{root}/activate/")
    assert success.status_code == 302
    assert "شاخ کی حالت تبدیل" in signed_in.get(success.url).text


@pytest.mark.parametrize(
    "role", [Role.FINANCE_REVIEWER, Role.BRANCH_LEAD, Role.HR_LEAD, Role.CONTENT_EDITOR]
)
def test_transition_service_denies_wrong_role(branch, role):
    actor = User.objects.create_user(
        email="denied@example.com", full_name="Denied", role=role
    )
    with pytest.raises(PermissionDenied):
        services.transition(actor, branch, "activate")
    branch.refresh_from_db()
    assert branch.status == BranchStatus.FORMING
    assert not AuditLog.objects.exists()


def test_t_assign_closed_keeps_history_and_rejects_new_assignments(
    admin, branch, clock
):
    lead = User.objects.create_user(
        email="lead@example.com", full_name="Lead", role=Role.BRANCH_LEAD
    )
    assignment = assign_branch(admin, lead, branch)
    services.transition(admin, branch, "close", "Branch complete")
    with pytest.raises(ValidationError, match="Closed branches"):
        assign_branch(admin, lead, branch)
    assert UserBranchAssignment.objects.get(pk=assignment.pk).branch_id == branch.pk
    assert AuditLog.objects.filter(action="assignment.added").count() == 1


def test_failed_audit_rolls_back_transition(admin, branch):
    before = Branch.objects.values().get(pk=branch.pk)
    with patch(
        "apps.branches.services.audit.record",
        side_effect=RuntimeError("audit unavailable"),
    ):
        with pytest.raises(RuntimeError):
            services.transition(admin, branch, "activate")
    assert Branch.objects.values().get(pk=branch.pk) == before


@pytest.mark.django_db(transaction=True)
def test_concurrent_activation_checks_locked_state(admin, branch):
    barrier = Barrier(2)

    def activate():
        try:
            barrier.wait(timeout=20)
            try:
                services.transition(admin, branch, "activate")
                return "activated"
            except services.InvalidTransition:
                return "conflict"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda index: activate(), range(2)))
    assert sorted(results) == ["activated", "conflict"]
    assert AuditLog.objects.filter(action="branch.activated").count() == 1
