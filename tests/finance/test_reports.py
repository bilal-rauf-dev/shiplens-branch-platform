from datetime import date, datetime
from decimal import Decimal
from io import StringIO

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction

from apps.accounts.models import Role, User, UserBranchAssignment
from apps.audit.models import AuditLog
from apps.branches.models import BranchStatus
from apps.finance import services
from apps.finance.models import WeeklyReport
from apps.finance.report_fields import REPORT_FIELDS
from apps.finance.report_forms import ReportNarrativeForm
from apps.finance.report_selectors import report_aggregates, week_bounds
from apps.finance.report_services import ensure_drafts
from apps.volunteers import services as volunteer_services
from apps.volunteers.forms import ApplicationForm
from apps.volunteers.models import Member, MemberStatus, VolunteerRole

pytestmark = pytest.mark.django_db


def open_on(branch, when=date(2026, 10, 1)):
    branch.opened_on = when
    branch.save(update_fields=["opened_on"])
    return branch


@pytest.mark.parametrize(
    "timestamp,start",
    [
        ("2026-10-25T23:30:00+05:00", date(2026, 10, 19)),
        ("2026-10-26T00:30:00+05:00", date(2026, 10, 26)),
        ("2026-10-25T19:30:00+00:00", date(2026, 10, 26)),
    ],
)
def test_t_rpt_week(timestamp, start):
    actual_start, end = week_bounds(datetime.fromisoformat(timestamp))
    assert actual_start == start and (end - start).days == 6


def test_t_rpt_autodraft_idempotent(branch):
    reports = ensure_drafts(open_on(branch))
    assert [item.week_start for item in reports] == [
        date(2026, 9, 28),
        date(2026, 10, 5),
        date(2026, 10, 12),
        date(2026, 10, 19),
    ]
    assert [item.pk for item in ensure_drafts(branch)] == [item.pk for item in reports]
    events = AuditLog.objects.filter(action="report.drafted")
    assert events.count() == 4
    assert set(events.values_list("actor_label", flat=True)) == {"system"}
    call_command("generate_weekly_drafts", stdout=StringIO())
    assert WeeklyReport.objects.count() == 4 and events.count() == 4


def test_historical_draft_targets_only_the_requested_week(branch):
    open_on(branch)
    reports = ensure_drafts(branch, week_start=date(2026, 10, 5))
    assert [item.week_start for item in reports] == [date(2026, 10, 5)]
    assert WeeklyReport.objects.count() == 1
    assert ensure_drafts(branch, week_start=date(2026, 10, 5))[0].pk == reports[0].pk


@pytest.mark.parametrize(
    "week", [date(2026, 9, 21), date(2026, 10, 6), date(2026, 10, 26)]
)
def test_historical_draft_rejects_week_outside_branch_history(branch, week):
    with pytest.raises(ValidationError):
        ensure_drafts(open_on(branch), week_start=week)
    assert not WeeklyReport.objects.exists()


@pytest.mark.parametrize(
    "status", [BranchStatus.FORMING, BranchStatus.PAUSED, BranchStatus.CLOSED]
)
def test_inactive_branches_get_no_drafts(branch, status):
    open_on(branch)
    branch.status = status
    branch.save(update_fields=["status"])
    assert ensure_drafts(branch) == []


@pytest.mark.parametrize(
    "fields",
    [
        {"week_start": date(2026, 10, 20), "week_end": date(2026, 10, 26)},
        {"week_end": date(2026, 10, 24)},
        {"status": "UNKNOWN"},
        {"status": "LOCKED"},
        {"revision": -1},
    ],
)
def test_report_database_constraints(branch, fields):
    with pytest.raises(IntegrityError), transaction.atomic():
        WeeklyReport.objects.create(
            **{
                "branch": branch,
                "week_start": date(2026, 10, 19),
                "week_end": date(2026, 10, 25),
                **fields,
            }
        )


def test_t_rpt_unique(branch):
    report = ensure_drafts(open_on(branch))[0]
    with pytest.raises(IntegrityError), transaction.atomic():
        WeeklyReport.objects.create(
            branch=branch, week_start=report.week_start, week_end=report.week_end
        )


def test_t_rpt_field_registry(monkeypatch):
    good = {
        "activities": "Community teaching activities",
        "volunteer_hours": 10,
        "issues": "",
    }
    assert ReportNarrativeForm(good).is_valid()
    for field, value in [
        ("activities", "short"),
        ("volunteer_hours", -1),
        ("volunteer_hours", 10001),
        ("issues", "x" * 2001),
    ]:
        assert not ReportNarrativeForm({**good, field: value}).is_valid()
    monkeypatch.setitem(
        REPORT_FIELDS,
        "extra",
        {"type": "text", "label": "Extra", "required": True, "min_length": 3},
    )
    assert not ReportNarrativeForm(good).is_valid()
    assert ReportNarrativeForm({**good, "extra": "One registry entry"}).is_valid()


def test_t_rpt_aggregates_spanning_months(bl, branch, collection_data, clock):
    clock.move_to("2026-11-02T10:00:00+05:00")
    first = services.create_collection(
        bl,
        branch,
        {
            **collection_data,
            "collection_date": date(2026, 10, 31),
            "amount": Decimal("100.10"),
        },
    )
    services.create_collection(
        bl,
        branch,
        {
            **collection_data,
            "receipt_no": "SECOND",
            "collection_date": date(2026, 11, 1),
            "method": "CHEQUE",
            "amount": Decimal("25.00"),
        },
    )
    voided = services.create_collection(
        bl,
        branch,
        {**collection_data, "receipt_no": "VOID", "collection_date": date(2026, 11, 1)},
    )
    services.void_collection(bl, voided, "Duplicate receipt")
    services.create_transfer(bl, branch, [first.pk], date(2026, 11, 2), "LATER-BANK")
    result = report_aggregates(branch, date(2026, 10, 26))
    assert result["total_amount"] == Decimal("125.10") and result["entry_count"] == 2
    assert result["by_method"] == {
        "CASH": Decimal("100.10"),
        "CHEQUE": Decimal("25.00"),
        "BANK_DEPOSIT": Decimal("0.00"),
    }
    assert result["unsent_amount_at_week_end"] == Decimal("125.10")
    assert result["new_members"] == result["active_members_end"] == 0
    assert (
        result["applications_received"]
        == result["applications_accepted"]
        == result["applications_declined"]
        == 0
    )


def test_report_member_and_application_counts(branch):
    hr = User.objects.create_user(
        email="report-hr@example.com", full_name="Report HR", role=Role.HR_LEAD
    )
    UserBranchAssignment.objects.create(user=hr, branch=branch, created_by=hr)
    role = VolunteerRole.objects.get(code="VOLUNTEER")
    for index in range(2):
        form = ApplicationForm(
            {
                "full_name": "Report Applicant",
                "email": f"report{index}@example.com",
                "phone": f"0300123456{index}",
                "date_of_birth": "2000-01-01",
                "preferred_branch": branch.pk,
                "interests": ["education"],
                "availability": ["weekends"],
                "motivation": "Teaching at the local community centre.",
                "preferred_language": "en",
                "privacy_consent": True,
            }
        )
        assert form.is_valid(), form.errors
        app = volunteer_services.submit_application(form.cleaned_data, None)
        if index == 0:
            volunteer_services.accept_application(hr, app.pk, role_id=role.pk)
        else:
            volunteer_services.decline_application(hr, app.pk, "No capacity this week")
    Member.objects.create(
        member_id="M-2026-99999",
        branch=branch,
        volunteer_role=role,
        full_name="Inactive Member",
        email="inactive-report@example.com",
        phone="+923001234569",
        joined_on=date(2026, 10, 24),
        status=MemberStatus.INACTIVE,
        created_by=hr,
        updated_by=hr,
    )
    figures = report_aggregates(branch, date(2026, 10, 19))
    assert figures["new_members"] == 2 and figures["active_members_end"] == 1
    assert figures["applications_received"] == 2
    assert figures["applications_accepted"] == figures["applications_declined"] == 1
