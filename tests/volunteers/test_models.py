import pytest
from django.db import DatabaseError, IntegrityError, transaction

from apps.volunteers import services
from apps.volunteers.forms import ApplicationForm
from apps.volunteers.models import (
    Application,
    Member,
    MemberStatus,
    Team,
    VolunteerRole,
)

pytestmark = pytest.mark.django_db


def test_volunteer_roles_are_seeded_in_urdu():
    assert dict(VolunteerRole.objects.values_list("code", "name_ur")) == {
        "VOLUNTEER": "رضاکار",
        "TEAM_LEAD": "ٹیم سربراہ",
        "COORDINATOR": "رابطہ کار",
        "TREASURER": "خزانچی",
    }
    assert str(VolunteerRole.objects.get(code="VOLUNTEER")) == "Volunteer"


@pytest.mark.parametrize(
    "fields",
    [
        {"status": "UNKNOWN"},
        {"preferred_language": "xx"},
        {"status": "ACCEPTED"},
        {"status": "DECLINED", "decision_note": ""},
        {"status": "DECLINED", "decision_note": "    "},
        {"motivation": "x" * 19},
        {"motivation": "x" * 1001},
    ],
)
def test_application_database_checks(valid_data, fields):
    form = ApplicationForm(valid_data)
    assert form.is_valid()
    application = services.submit_application(form.cleaned_data, None)
    assert str(application) == application.reference
    with pytest.raises(IntegrityError), transaction.atomic():
        Application.objects.filter(pk=application.pk).update(**fields)


def test_application_accepted_iff_member_linked(valid_data, member_factory):
    form = ApplicationForm(valid_data)
    assert form.is_valid()
    application = services.submit_application(form.cleaned_data, None)
    member = member_factory(application=application)
    with pytest.raises(IntegrityError), transaction.atomic():
        Application.objects.filter(pk=application.pk).update(member=member)
    Application.objects.filter(pk=application.pk).update(
        member=member, status="ACCEPTED"
    )
    application.refresh_from_db()
    assert application.member == member


def test_t_team_unique_and_composite_branch_constraint(
    branch, branch_factory, member_factory
):
    team = Team.objects.create(branch=branch, name="Teaching")
    assert str(team) == "Teaching"
    with pytest.raises(IntegrityError), transaction.atomic():
        Team.objects.create(branch=branch, name="TEACHING")
    other_branch = branch_factory(code="BR-LHE-01", name_en="Lahore")
    other_team = Team.objects.create(branch=other_branch, name="Teaching")
    with pytest.raises(IntegrityError), transaction.atomic():
        member_factory(team=other_team)
    assert member_factory(team=team).team == team


def test_t_mem_email_unique_and_immutable_id(member_factory):
    member = member_factory()
    assert str(member) == "M-2026-00001"
    with pytest.raises(IntegrityError), transaction.atomic():
        member_factory(member_id="M-2026-00002", email="EXISTING@EXAMPLE.COM")
    left = member_factory(
        member_id="M-2026-00003",
        email="EXISTING@EXAMPLE.COM",
        status=MemberStatus.LEFT,
        left_on="2026-10-25",
    )
    assert left.status == MemberStatus.LEFT
    with pytest.raises(DatabaseError, match="immutable"), transaction.atomic():
        Member.objects.filter(pk=member.pk).update(member_id="M-2026-99999")


@pytest.mark.parametrize(
    "fields",
    [
        {"status": "UNKNOWN"},
        {"status": MemberStatus.LEFT, "left_on": None},
        {"status": MemberStatus.ACTIVE, "left_on": "2026-10-25"},
        {"status": MemberStatus.LEFT, "left_on": "2026-09-30"},
    ],
)
def test_t_mem_left_on_checks(member_factory, fields):
    with pytest.raises(IntegrityError), transaction.atomic():
        member_factory(**fields)
