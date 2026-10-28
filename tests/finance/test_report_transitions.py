from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import Role, User
from apps.audit.models import AuditLog
from apps.core.exceptions import InvalidTransition
from apps.finance import report_services
from apps.finance import services as finance_services
from apps.finance.models import ReportStatus, WeeklyReportLine

pytestmark = pytest.mark.django_db
NARRATIVE = {
    "activities": "Teaching sessions and community support.",
    "volunteer_hours": 12,
    "issues": "",
}


@pytest.fixture
def report_setup(bl, branch, collection_data, clock):
    clock.move_to("2026-10-25T10:00:00+05:00")
    collection = finance_services.create_collection(
        bl, branch, {**collection_data, "amount": Decimal("3500.00")}
    )
    branch.opened_on = date(2026, 10, 19)
    branch.save(update_fields=["opened_on"])
    report = report_services.ensure_drafts(branch)[0]
    reviewer = User.objects.create_user(
        email="reviewer-reports@example.com",
        full_name="Finance Reviewer",
        role=Role.FINANCE_REVIEWER,
    )
    clock.move_to("2026-10-26T10:00:00+05:00")
    return {"report": report, "collection": collection, "reviewer": reviewer}


def test_report_service_lifecycle_and_frozen_revisions(bl, report_setup):
    report = report_setup["report"]
    submitted = report_services.transition(bl, report, "submit", narrative=NARRATIVE)
    assert submitted.revision == 1 and submitted.snapshot["total_amount"] == "3500.00"
    assert len(submitted.snapshot_hash) == 64
    assert finance_services.week_is_closed(report.branch, report.week_start)
    returned = report_services.transition(
        report_setup["reviewer"],
        report,
        "return",
        expected_revision=1,
        comment="Please correct the amount",
    )
    assert returned.status == ReportStatus.RETURNED
    assert not finance_services.week_is_closed(report.branch, report.week_start)
    item = report_setup["collection"]
    finance_services.update_collection(
        bl,
        item,
        {
            "collection_date": item.collection_date,
            "amount": Decimal("3600.00"),
            "method": item.method,
            "receipt_no": item.receipt_no,
            "source_note": item.source_note,
        },
    )
    resubmitted = report_services.transition(
        bl, report, "resubmit", narrative=NARRATIVE
    )
    assert (
        resubmitted.revision == 2 and resubmitted.snapshot["total_amount"] == "3600.00"
    )
    assert WeeklyReportLine.objects.get(report=report, revision=1).amount == Decimal(
        "3500.00"
    )
    assert WeeklyReportLine.objects.get(report=report, revision=2).amount == Decimal(
        "3600.00"
    )
    approved = report_services.transition(
        report_setup["reviewer"], report, "approve", expected_revision=2
    )
    assert approved.status == ReportStatus.LOCKED and approved.locked_at is not None
    assert list(
        AuditLog.objects.filter(entity_type="weeklyreport", entity_id=report.pk)
        .order_by("pk")
        .values_list("action", flat=True)
    ) == [
        "report.drafted",
        "report.submitted",
        "report.returned",
        "report.resubmitted",
        "report.approved",
        "report.locked",
    ]


def test_report_guards_and_narrative(bl, report_setup, clock, settings):
    report = report_setup["report"]
    with pytest.raises(ValidationError):
        report_services.save_narrative(bl, report, {"activities": "short"})
    saved = report_services.save_narrative(bl, report, NARRATIVE)
    assert saved.narrative == NARRATIVE and saved.revision == 0
    clock.move_to("2026-10-25T23:59:00+05:00")
    with pytest.raises(InvalidTransition):
        report_services.transition(bl, report, "submit")
    settings.BUSINESS_RULES = {
        **settings.BUSINESS_RULES,
        "allow_submit_current_week": True,
    }
    report_services.transition(bl, report, "submit")
    with pytest.raises(InvalidTransition):
        report_services.save_narrative(bl, report, NARRATIVE)
    with pytest.raises(PermissionDenied):
        report_services.transition(bl, report, "approve", expected_revision=1)
    with pytest.raises(PermissionDenied):
        report_services.transition(report_setup["reviewer"], report, "submit")
    with pytest.raises(InvalidTransition):
        report_services.transition(
            report_setup["reviewer"], report, "approve", expected_revision=0
        )
    with pytest.raises(ValidationError):
        report_services.transition(
            report_setup["reviewer"], report, "return", expected_revision=1, comment=""
        )


def test_approval_audit_failure_rolls_back_both_states(bl, report_setup):
    report = report_services.transition(
        bl, report_setup["report"], "submit", narrative=NARRATIVE
    )
    original_record = report_services.audit.record

    def fail_on_lock(actor, action, **kwargs):
        if action == "report.locked":
            raise RuntimeError("audit unavailable")
        return original_record(actor, action, **kwargs)

    with patch("apps.finance.report_services.audit.record", side_effect=fail_on_lock):
        with pytest.raises(RuntimeError):
            report_services.transition(
                report_setup["reviewer"], report, "approve", expected_revision=1
            )
    report.refresh_from_db()
    assert report.status == ReportStatus.SUBMITTED and report.locked_at is None
    assert not AuditLog.objects.filter(action="report.approved").exists()
