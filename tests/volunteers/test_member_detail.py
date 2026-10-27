from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db import connections
from django.http import Http404
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.audit.models import AuditLog
from apps.core import clock as business_clock
from apps.core.exceptions import InvalidTransition
from apps.volunteers import services
from apps.volunteers.forms import MemberEditForm
from apps.volunteers.models import MemberStatus, Team, VolunteerRole

pytestmark = pytest.mark.django_db


@pytest.fixture
def sa():
    return User.objects.create_user(
        email="member-admin@example.com", full_name="Admin", role=Role.SUPER_ADMIN
    )


@pytest.mark.parametrize("status", MemberStatus.values)
@pytest.mark.parametrize(
    "action", ["deactivate", "reactivate", "mark_left", "reinstate"]
)
def test_t_mem_status_every_state_action(sa, member_factory, status, action, clock):
    member = member_factory(
        status=status,
        left_on=date(2026, 10, 10) if status == MemberStatus.LEFT else None,
    )
    before = AuditLog.objects.count()
    clock.shift(60)
    expected = {
        (MemberStatus.ACTIVE, "deactivate"): MemberStatus.INACTIVE,
        (MemberStatus.INACTIVE, "reactivate"): MemberStatus.ACTIVE,
        (MemberStatus.ACTIVE, "mark_left"): MemberStatus.LEFT,
        (MemberStatus.INACTIVE, "mark_left"): MemberStatus.LEFT,
        (MemberStatus.LEFT, "reinstate"): MemberStatus.ACTIVE,
    }
    if (status, action) not in expected:
        with pytest.raises(InvalidTransition):
            services.transition_member(
                sa, member.pk, action, left_on=date(2026, 10, 20), reason="Returning"
            )
        member.refresh_from_db()
        assert member.status == status and AuditLog.objects.count() == before
    else:
        updated = services.transition_member(
            sa, member.pk, action, left_on=date(2026, 10, 20), reason="Returning"
        )
        assert updated.status == expected[status, action]
        assert updated.updated_at == business_clock.now() and updated.updated_by == sa
        assert updated.left_on == (
            date(2026, 10, 20) if action == "mark_left" else None
        )
        event = AuditLog.objects.latest("pk")
        assert event.action == (
            "member.reinstated" if action == "reinstate" else "member.status_changed"
        )
        assert event.actor == sa and event.before["status"] == status
        if action == "reinstate":
            assert event.metadata == {"reason": "Returning"}


def test_t_mem_email_unique_on_reinstate(sa, member_factory):
    left = member_factory(status=MemberStatus.LEFT, left_on=date(2026, 10, 20))
    member_factory(member_id="M-2026-00002", email=left.email.upper())
    with pytest.raises(ValidationError, match="already uses"):
        services.transition_member(sa, left.pk, "reinstate", reason="Returning")
    left.refresh_from_db()
    assert left.status == MemberStatus.LEFT
    assert not AuditLog.objects.filter(action="member.reinstated").exists()


def test_leaving_date_and_reinstate_reason_required(sa, member_factory):
    member = member_factory()
    for left_on in (None, date(2026, 9, 30)):
        with pytest.raises(ValidationError):
            services.transition_member(sa, member.pk, "mark_left", left_on=left_on)
    services.transition_member(sa, member.pk, "mark_left", left_on=date(2026, 10, 1))
    with pytest.raises(ValidationError):
        services.transition_member(sa, member.pk, "reinstate", reason="   ")


def test_t_sec_mass_assign_member_edit(
    client, reviewer, member_factory, branch_factory, clock
):
    member = member_factory()
    other = branch_factory(code="BR-LHE-01")
    client.force_login(reviewer)
    url = reverse("member-edit", args=[member.pk])
    assert client.get(url).status_code == 200
    clock.shift(60)
    response = client.post(
        url,
        {
            "team_id": "",
            "role_id": member.volunteer_role_id,
            "phone": "+923001234567",
            "notes": "Updated notes",
            "member_id": "HACKED",
            "branch": other.pk,
            "branch_id": other.pk,
            "status": "LEFT",
            "email": "hacked@example.com",
            "created_by": reviewer.pk,
        },
    )
    assert response.status_code == 302 and response.url == reverse(
        "member-detail", args=[member.pk]
    )
    member.refresh_from_db()
    assert member.member_id == "M-2026-00001" and member.branch_id != other.pk
    assert (
        member.status == MemberStatus.ACTIVE and member.email == "existing@example.com"
    )
    assert member.notes == "Updated notes" and member.updated_at == business_clock.now()
    detail = client.get(response.url)
    assert "Member updated." in detail.text and "Updated notes" in detail.text
    assert "Member updated" in detail.text and "History" in detail.text
    assert detail["Cache-Control"] == "no-store, private"


def test_bl_can_view_history_but_cannot_edit_or_transition(
    client, reviewer, member_factory
):
    member = member_factory()
    reviewer.role = Role.BRANCH_LEAD
    reviewer.save(update_fields=["role"])
    client.force_login(reviewer)
    response = client.get(reverse("member-detail", args=[member.pk]))
    assert response.status_code == 200 and "Edit member" not in response.text
    for route in (
        "member-edit",
        "member-deactivate",
        "member-reactivate",
        "member-mark-left",
        "member-reinstate",
    ):
        assert client.post(reverse(route, args=[member.pk])).status_code == 403


def test_member_edit_and_transition_outside_scope_are_404(
    client, reviewer, member_factory, branch_factory
):
    member = member_factory(branch=branch_factory(code="BR-LHE-01"))
    client.force_login(reviewer)
    for route in ("member-detail", "member-edit"):
        assert client.get(reverse(route, args=[member.pk])).status_code == 404
    assert (
        client.post(reverse("member-deactivate", args=[member.pk])).status_code == 404
    )
    with pytest.raises(Http404):
        services.transition_member(reviewer, member.pk, "deactivate")


def test_t_mem_team_branch_edit_rejected(reviewer, member_factory, branch_factory):
    member = member_factory()
    foreign = Team.objects.create(
        branch=branch_factory(code="BR-LHE-01"), name="Foreign"
    )
    with pytest.raises(ValidationError):
        services.update_member(
            reviewer,
            member.pk,
            team_id=foreign.pk,
            role_id=member.volunteer_role_id,
            phone=member.phone,
            notes="",
        )
    form = MemberEditForm(
        {
            "team_id": foreign.pk,
            "role_id": member.volunteer_role_id,
            "phone": member.phone,
        },
        member=member,
    )
    assert not form.is_valid() and "team_id" in form.errors


def test_edit_preserves_existing_inactive_choices(reviewer, member_factory, branch):
    team = Team.objects.create(branch=branch, name="Old team", is_active=False)
    role = VolunteerRole.objects.get(code="VOLUNTEER")
    role.is_active = False
    role.save(update_fields=["is_active"])
    member = member_factory(team=team)
    form = MemberEditForm(
        {
            "team_id": team.pk,
            "role_id": role.pk,
            "phone": member.phone,
            "notes": "Kept history",
        },
        member=member,
    )
    assert form.is_valid(), form.errors
    updated = services.update_member(
        reviewer,
        member.pk,
        team_id=team.pk,
        role_id=role.pk,
        phone=member.phone,
        notes="Kept history",
    )
    assert updated.team == team


def test_member_transition_http_prg_errors_and_sa_reinstatement(
    client, reviewer, sa, member_factory
):
    member = member_factory()
    client.force_login(reviewer)
    deactivate = reverse("member-deactivate", args=[member.pk])
    assert client.get(deactivate).status_code == 405
    response = client.post(deactivate)
    assert response.status_code == 302
    assert "Member status updated." in client.get(response.url).text
    assert client.post(deactivate).status_code == 409
    assert (
        client.post(
            reverse("member-mark-left", args=[member.pk]), {"left_on": "2026-09-30"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            reverse("member-mark-left", args=[member.pk]), {"left_on": "2026-10-10"}
        ).status_code
        == 302
    )
    reinstate = reverse("member-reinstate", args=[member.pk])
    assert client.post(reinstate, {"reason": "Returning"}).status_code == 403
    client.force_login(sa)
    assert client.post(reinstate).status_code == 400
    assert client.post(reinstate, {"reason": "Returning"}).status_code == 302


@pytest.mark.parametrize("operation", ["edit", "transition"])
def test_member_audit_failure_rolls_back(reviewer, member_factory, operation):
    member = member_factory()
    original_time = member.updated_at
    with patch(
        "apps.volunteers.services.audit.record",
        side_effect=RuntimeError("audit unavailable"),
    ):
        with pytest.raises(RuntimeError):
            if operation == "edit":
                services.update_member(
                    reviewer,
                    member.pk,
                    team_id=None,
                    role_id=member.volunteer_role_id,
                    phone=member.phone,
                    notes="New notes",
                )
            else:
                services.transition_member(reviewer, member.pk, "deactivate")
    member.refresh_from_db()
    assert member.notes == "" and member.status == MemberStatus.ACTIVE
    assert member.updated_at == original_time


@pytest.mark.django_db(transaction=True)
def test_t_mem_email_unique_concurrent_reinstatement(sa, member_factory):
    first = member_factory(status=MemberStatus.LEFT, left_on=date(2026, 10, 20))
    second = member_factory(
        member_id="M-2026-00002",
        email=first.email,
        status=MemberStatus.LEFT,
        left_on=date(2026, 10, 20),
    )
    barrier = Barrier(2)

    def reinstate(member_id):
        try:
            barrier.wait(timeout=10)
            try:
                services.transition_member(
                    sa, member_id, "reinstate", reason="Returning"
                )
                return "reinstated"
            except ValidationError:
                return "duplicate"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reinstate, [first.pk, second.pk]))
    assert sorted(results) == ["duplicate", "reinstated"]
    assert AuditLog.objects.filter(action="member.reinstated").count() == 1
