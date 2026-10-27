"""HR decisions are scoped, terminal and atomic with member creation."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db import connections
from django.http import Http404

from apps import audit
from apps.accounts.models import Role, User, UserBranchAssignment
from apps.audit.models import AuditLog
from apps.audit.selectors import verify_chain
from apps.branches.models import BranchStatus
from apps.core import clock as business_clock
from apps.core.exceptions import InvalidTransition
from apps.core.models import IdSequence
from apps.volunteers import services
from apps.volunteers.models import (
    Application,
    ApplicationStatus,
    Member,
    MemberStatus,
    Team,
)

pytestmark = pytest.mark.django_db


def test_t_mem_id_format_and_accept_fields(
    reviewer, application, volunteer_role, clock
):
    team = Team.objects.create(branch=application.preferred_branch, name="Teaching")
    clock.shift(60)
    member = services.accept_application(
        reviewer, application.pk, team_id=team.pk, role_id=volunteer_role.pk
    )
    application.refresh_from_db()
    assert member.member_id == "M-2026-00001"
    assert (
        member.application_id == application.pk and application.member_id == member.pk
    )
    assert member.branch_id == application.preferred_branch_id
    assert (member.full_name, member.email, member.phone) == (
        application.full_name,
        application.email,
        application.phone,
    )
    assert member.team_id == team.pk and member.volunteer_role_id == volunteer_role.pk
    assert (
        member.status == MemberStatus.ACTIVE
        and member.joined_on == business_clock.today()
    )
    assert member.created_by == member.updated_by == reviewer
    assert (
        member.created_at
        == member.updated_at
        == application.updated_at
        == application.decided_at
        == business_clock.now()
    )
    assert (
        application.status == ApplicationStatus.ACCEPTED
        and application.decided_by == reviewer
    )
    events = list(
        AuditLog.objects.filter(
            action__in=["application.accepted", "member.created"]
        ).order_by("pk")
    )
    assert [event.action for event in events] == [
        "application.accepted",
        "member.created",
    ]
    assert all(event.actor_id == reviewer.pk for event in events)
    assert events[0].after == {"status": "ACCEPTED", "member_id": member.pk}
    assert events[1].after["member_id"] == member.member_id
    assert verify_chain() == (True, None)


def test_member_id_uses_acceptance_year_in_karachi(
    reviewer, application, volunteer_role, clock
):
    assert application.reference == "APP-2026-00001"  # T-ID-REFS
    clock.move_to("2027-01-01T00:05:00+05:00")
    member = services.accept_application(
        reviewer, application.pk, role_id=volunteer_role.pk
    )
    assert member.member_id == "M-2027-00001"
    assert member.joined_on == date(2027, 1, 1)
    assert member.team_id is None


@pytest.mark.parametrize("initial", [None, 7])
def test_t_app_accept_atomic(reviewer, application, volunteer_role, initial):
    if initial is not None:
        IdSequence.objects.create(key="member:2026", last_value=initial)
    before = Application.objects.values().get(pk=application.pk)
    original_record = audit.record

    def fail_member_audit(actor, action, **fields):
        if action == "member.created":
            raise RuntimeError("member audit unavailable")
        return original_record(actor, action, **fields)

    with patch("apps.volunteers.services.audit.record", side_effect=fail_member_audit):
        with pytest.raises(RuntimeError, match="member audit unavailable"):
            services.accept_application(
                reviewer, application.pk, role_id=volunteer_role.pk
            )
    assert not Member.objects.exists()
    assert Application.objects.values().get(pk=application.pk) == before
    sequence = IdSequence.objects.filter(pk="member:2026").first()
    assert (sequence.last_value if sequence else None) == initial
    assert not AuditLog.objects.filter(action="application.accepted").exists()
    accepted = services.accept_application(
        reviewer, application.pk, role_id=volunteer_role.pk
    )
    assert accepted.member_id == f"M-2026-{(initial or 0) + 1:05d}"


@pytest.mark.parametrize("terminal", ["ACCEPTED", "DECLINED"])
@pytest.mark.parametrize("action", ["accept", "decline", "reassign"])
def test_t_app_terminal(reviewer, application, volunteer_role, terminal, action):
    if terminal == "ACCEPTED":
        services.accept_application(reviewer, application.pk, role_id=volunteer_role.pk)
    else:
        services.decline_application(reviewer, application.pk, "Not available")
    before = Application.objects.values().get(pk=application.pk)
    audit_count = AuditLog.objects.count()
    member_count = Member.objects.count()
    with pytest.raises(InvalidTransition):
        if action == "accept":
            services.accept_application(
                reviewer, application.pk, role_id=volunteer_role.pk
            )
        elif action == "decline":
            services.decline_application(reviewer, application.pk, "Another reason")
        else:
            services.reassign_branch(
                reviewer, application.pk, application.preferred_branch_id
            )
    assert Application.objects.values().get(pk=application.pk) == before
    assert (
        AuditLog.objects.count() == audit_count
        and Member.objects.count() == member_count
    )


@pytest.mark.parametrize("status", BranchStatus.values)
def test_accept_rechecks_branch_state(reviewer, application, volunteer_role, status):
    branch = application.preferred_branch
    branch.status = status
    branch.save(update_fields=["status"])
    if status == BranchStatus.CLOSED:
        with pytest.raises(InvalidTransition):
            services.accept_application(
                reviewer, application.pk, role_id=volunteer_role.pk
            )
        assert not Member.objects.exists()
    else:
        assert (
            services.accept_application(
                reviewer, application.pk, role_id=volunteer_role.pk
            ).status
            == MemberStatus.ACTIVE
        )


def test_t_mem_team_branch_rejects_foreign_and_missing_team(
    reviewer, application, volunteer_role, branch_factory
):
    other = branch_factory(code="BR-LHE-01", name_en="Lahore")
    team = Team.objects.create(branch=other, name="Other branch")
    for team_id in (team.pk, team.pk + 999):
        with pytest.raises(ValidationError):
            services.accept_application(
                reviewer, application.pk, team_id=team_id, role_id=volunteer_role.pk
            )
    assert not Member.objects.exists()
    assert not IdSequence.objects.filter(pk="member:2026").exists()


def test_accept_requires_existing_role(reviewer, application, volunteer_role):
    with pytest.raises(ValidationError):
        services.accept_application(
            reviewer, application.pk, role_id=volunteer_role.pk + 999
        )
    assert not Member.objects.exists()


def test_accept_cannot_duplicate_current_member_email(
    reviewer, application, volunteer_role, member_factory
):
    member_factory(email=application.email)
    with pytest.raises(ValidationError):
        services.accept_application(reviewer, application.pk, role_id=volunteer_role.pk)
    application.refresh_from_db()
    assert application.status == ApplicationStatus.PENDING
    assert Member.objects.count() == 1
    assert not IdSequence.objects.filter(pk="member:2026").exists()


@pytest.mark.parametrize("reason", ["12345", "x" * 500])
def test_decline_reason_boundaries_and_audit(reviewer, application, reason, clock):
    clock.shift(60)
    result = services.decline_application(reviewer, application.pk, f"  {reason}  ")
    assert (
        result.status == ApplicationStatus.DECLINED and result.decision_note == reason
    )
    assert result.decided_by == reviewer
    assert result.decided_at == result.updated_at == business_clock.now()
    assert result.member_id is None and not Member.objects.exists()
    event = AuditLog.objects.get(action="application.declined")
    assert event.after == {"status": "DECLINED", "decision_note": reason}


@pytest.mark.parametrize("reason", ["", "   ", "1234", "x" * 501])
def test_decline_rejects_invalid_reason(reviewer, application, reason):
    with pytest.raises(ValidationError):
        services.decline_application(reviewer, application.pk, reason)
    application.refresh_from_db()
    assert application.status == ApplicationStatus.PENDING
    assert not AuditLog.objects.filter(action="application.declined").exists()


def test_decline_reason_bounds_come_from_rules(reviewer, application, settings):
    settings.BUSINESS_RULES = {
        **settings.BUSINESS_RULES,
        "application_decline_reason_min_length": 8,
        "application_decline_reason_max_length": 10,
    }
    for reason in ("1234567", "12345678901"):
        with pytest.raises(ValidationError):
            services.decline_application(reviewer, application.pk, reason)
    assert (
        services.decline_application(reviewer, application.pk, "12345678").status
        == ApplicationStatus.DECLINED
    )


@pytest.mark.parametrize("status", BranchStatus.values)
def test_reassignment_target_and_source_scope(
    reviewer, application, branch_factory, status
):
    target = branch_factory(code="BR-LHE-01", name_en="Lahore", status=status)
    if status in {BranchStatus.PAUSED, BranchStatus.CLOSED}:
        with pytest.raises(ValidationError):
            services.reassign_branch(reviewer, application.pk, target.pk)
        application.refresh_from_db()
        assert application.preferred_branch_id != target.pk
        assert not AuditLog.objects.filter(action="application.reassigned").exists()
    else:
        previous = application.preferred_branch_id
        moved = services.reassign_branch(reviewer, application.pk, target.pk)
        assert (
            moved.preferred_branch_id == target.pk
            and moved.status == ApplicationStatus.PENDING
        )
        event = AuditLog.objects.get(action="application.reassigned")
        assert event.before == {"preferred_branch_id": previous}
        assert event.after == {"preferred_branch_id": target.pk}
        assert event.branch_id == target.pk
        # No target assignment: moving the record removes the actor's visibility.
        with pytest.raises(Http404):
            services.decline_application(reviewer, application.pk, "Out of scope")


def test_sa_can_reassign_and_missing_target_is_rejected(application, branch_factory):
    actor = User.objects.create_user(
        email="admin-review@example.com", full_name="Admin", role=Role.SUPER_ADMIN
    )
    target = branch_factory(code="BR-LHE-01", name_en="Lahore")
    with pytest.raises(ValidationError):
        services.reassign_branch(actor, application.pk, target.pk + 999)
    assert (
        services.reassign_branch(actor, application.pk, target.pk).preferred_branch_id
        == target.pk
    )


@pytest.mark.parametrize("action", ["accept", "decline", "reassign"])
def test_hr_cannot_mutate_an_unassigned_application(
    admin, application, volunteer_role, action
):
    with pytest.raises(Http404):
        if action == "accept":
            services.accept_application(
                admin, application.pk, role_id=volunteer_role.pk
            )
        elif action == "decline":
            services.decline_application(admin, application.pk, "No assignment")
        else:
            services.reassign_branch(
                admin, application.pk, application.preferred_branch_id
            )


@pytest.mark.parametrize("action", ["decline", "reassign"])
def test_audit_failure_rolls_back_other_decisions(
    reviewer, application, branch_factory, action
):
    target = branch_factory(code="BR-LHE-01", name_en="Lahore")
    before = Application.objects.values().get(pk=application.pk)
    with patch(
        "apps.volunteers.services.audit.record",
        side_effect=RuntimeError("audit unavailable"),
    ):
        with pytest.raises(RuntimeError):
            if action == "decline":
                services.decline_application(reviewer, application.pk, "No capacity")
            else:
                services.reassign_branch(reviewer, application.pk, target.pk)
    assert Application.objects.values().get(pk=application.pk) == before


@pytest.mark.django_db(transaction=True)
def test_t_app_accept_race(reviewer, application, volunteer_role):
    other = User.objects.create_user(
        email="second-hr@example.com", full_name="Second HR", role=Role.HR_LEAD
    )
    UserBranchAssignment.objects.create(
        user=other, branch_id=application.preferred_branch_id, created_by=reviewer
    )
    barrier = Barrier(2)

    def accept(actor):
        try:
            barrier.wait(timeout=20)
            try:
                services.accept_application(
                    actor, application.pk, role_id=volunteer_role.pk
                )
                return "accepted"
            except InvalidTransition:
                return "already decided"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(accept, [reviewer, other]))
    assert sorted(results) == ["accepted", "already decided"]
    assert Member.objects.count() == 1
    assert AuditLog.objects.filter(action="member.created").count() == 1
    assert AuditLog.objects.filter(action="application.accepted").count() == 1
    assert IdSequence.objects.get(pk="member:2026").last_value == 1
    assert verify_chain() == (True, None)


@pytest.mark.django_db(transaction=True)
def test_t_mem_id_race(
    reviewer, volunteer_role, branch, branch_factory, application_factory
):
    branches = [branch] + [
        branch_factory(code=f"BR-KHI-{number:02d}", name_en=f"Race {number}")
        for number in range(2, 11)
    ]
    for other in branches[1:]:
        UserBranchAssignment.objects.create(
            user=reviewer, branch=other, created_by=reviewer
        )
    applications = [
        application_factory(
            email=f"applicant-{index}@example.com",
            phone=f"+9230012345{index:02d}",
            preferred_branch=row.pk,
        )
        for index, row in enumerate(branches)
    ]
    barrier = Barrier(10)

    def accept(application):
        try:
            barrier.wait(timeout=20)
            return services.accept_application(
                reviewer, application.pk, role_id=volunteer_role.pk
            ).member_id
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=10) as pool:
        member_ids = list(pool.map(accept, applications))
    assert sorted(member_ids) == [f"M-2026-{number:05d}" for number in range(1, 11)]
    assert Member.objects.count() == 10
    assert Application.objects.filter(status=ApplicationStatus.ACCEPTED).count() == 10
    assert IdSequence.objects.get(pk="member:2026").last_value == 10
    assert verify_chain() == (True, None)
