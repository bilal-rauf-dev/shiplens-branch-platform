import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from django.db import DatabaseError, connection, connections, transaction
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.audit.models import AuditLog
from apps.audit.selectors import verify_chain
from apps.audit.services import canonical_json
from apps.core import clock as business_clock
from apps.core.exceptions import InvalidTransition
from apps.finance import report_services, services
from apps.finance.models import ReportStatus, WeeklyReport, WeeklyReportLine
from tests.rbac.registry import REPORT_NARRATIVE

pytestmark = pytest.mark.django_db


@pytest.fixture
def acceptance_setup(bl, branch, collection_data, clock):
    clock.move_to("2026-10-26T10:00:00+05:00")
    branch.opened_on = date(2026, 10, 19)
    branch.save(update_fields=["opened_on"])
    item = services.create_collection(
        bl,
        branch,
        {
            **collection_data,
            "collection_date": date(2026, 10, 25),
            "amount": Decimal("3500.00"),
        },
    )
    reviewer = User.objects.create_user(
        email="acceptance-fr@example.com",
        full_name="Finance Reviewer",
        role=Role.FINANCE_REVIEWER,
    )
    lead_client, reviewer_client = Client(), Client()
    lead_client.force_login(bl)
    reviewer_client.force_login(reviewer)
    request_id = uuid4()
    assert (
        lead_client.get(
            reverse("report-list"), HTTP_X_REQUEST_ID=str(request_id)
        ).status_code
        == 200
    )
    report = WeeklyReport.objects.get(branch=branch, week_start=date(2026, 10, 19))
    return {
        "report": report,
        "item": item,
        "reviewer": reviewer,
        "lead_client": lead_client,
        "reviewer_client": reviewer_client,
        "draft_request_id": request_id,
    }


def post(client, route, report, payload):
    request_id = uuid4()
    response = client.post(
        reverse(route, args=[report.pk]), payload, HTTP_X_REQUEST_ID=str(request_id)
    )
    return response, request_id


def submit(case):
    response, request_id = post(
        case["lead_client"], "report-submit", case["report"], REPORT_NARRATIVE
    )
    assert response.status_code == 302
    return request_id


def test_t_rpt_lifecycle(acceptance_setup, bl):
    case = acceptance_setup
    report = case["report"]
    submit_id = submit(case)
    report.refresh_from_db()
    assert (
        report.status == ReportStatus.SUBMITTED
        and report.snapshot["total_amount"] == "3500.00"
    )
    response, return_id = post(
        case["reviewer_client"],
        "report-return",
        report,
        {"expected_revision": 1, "comment": "Please check the narrative"},
    )
    assert response.status_code == 302
    response, resubmit_id = post(
        case["lead_client"], "report-resubmit", report, REPORT_NARRATIVE
    )
    assert response.status_code == 302
    response, approve_id = post(
        case["reviewer_client"], "report-approve", report, {"expected_revision": 2}
    )
    assert response.status_code == 302
    report.refresh_from_db()
    assert report.status == ReportStatus.LOCKED and report.revision == 2
    assert report.locked_at is not None and report.approved_by == case["reviewer"]
    rows = list(
        AuditLog.objects.filter(
            entity_type="weeklyreport", entity_id=report.pk
        ).order_by("pk")
    )
    assert [row.action for row in rows] == [
        "report.drafted",
        "report.submitted",
        "report.returned",
        "report.resubmitted",
        "report.approved",
        "report.locked",
    ]
    # System events have no User FK/role in the existing audit convention.
    assert [row.actor_role for row in rows] == [
        "",
        Role.BRANCH_LEAD,
        Role.FINANCE_REVIEWER,
        Role.BRANCH_LEAD,
        Role.FINANCE_REVIEWER,
        "",
    ]
    assert rows[0].actor_label == rows[-1].actor_label == "system"
    assert [row.request_id for row in rows] == [
        case["draft_request_id"],
        submit_id,
        return_id,
        resubmit_id,
        approve_id,
        approve_id,
    ]
    assert all(isinstance(row.request_id, UUID) and row.actor_label for row in rows)
    assert verify_chain() == (True, None)
    with (
        pytest.raises(DatabaseError, match="Weekly report is locked"),
        transaction.atomic(),
    ):
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE weekly_reports SET status = 'DRAFT' WHERE id = %s", [report.pk]
            )
    response = case["lead_client"].post(
        reverse("collection-edit", args=[case["item"].pk]),
        {
            "collection_date": date(2026, 10, 25),
            "amount": "3501.00",
            "method": "CASH",
            "receipt_no": "R-001",
        },
    )
    assert response.status_code == 409 and "week is closed" in response.text
    detail = case["lead_client"].get(reverse("report-detail", args=[report.pk]))
    assert "Approved figures" in detail.text and "Locked" in detail.text
    assert "Save narrative" not in detail.text and "Approve and lock" not in detail.text


def test_report_http_forbidden_roles(acceptance_setup):
    case = acceptance_setup
    report = case["report"]
    for route in ("report-return", "report-approve"):
        response, _ = post(
            case["lead_client"],
            route,
            report,
            {"expected_revision": 0, "comment": "Some details"},
        )
        assert response.status_code == 403
    response, _ = post(
        case["reviewer_client"], "report-submit", report, REPORT_NARRATIVE
    )
    assert response.status_code == 403


def test_stale_review_and_empty_return_comment(acceptance_setup):
    case = acceptance_setup
    submit(case)
    response, _ = post(
        case["reviewer_client"],
        "report-approve",
        case["report"],
        {"expected_revision": 0},
    )
    assert response.status_code == 409
    response, _ = post(
        case["reviewer_client"],
        "report-return",
        case["report"],
        {"expected_revision": 1, "comment": ""},
    )
    assert response.status_code == 400
    case["report"].refresh_from_db()
    assert case["report"].status == ReportStatus.SUBMITTED


def test_submit_current_week_refused(acceptance_setup, branch):
    case = acceptance_setup
    report = WeeklyReport.objects.get(branch=branch, week_start=date(2026, 10, 26))
    response, _ = post(case["lead_client"], "report-submit", report, REPORT_NARRATIVE)
    assert response.status_code == 409


def test_t_rpt_snapshot_and_t_col_week_closed(acceptance_setup):
    case = acceptance_setup
    report, item = case["report"], case["item"]
    submit(case)
    data = {
        "collection_date": date(2026, 10, 25),
        "amount": "3600.00",
        "method": "CASH",
        "receipt_no": item.receipt_no,
    }
    url = reverse("collection-edit", args=[item.pk])
    assert case["lead_client"].post(url, data).status_code == 409
    assert (
        post(
            case["reviewer_client"],
            "report-return",
            report,
            {"expected_revision": 1, "comment": "Please fix the amount"},
        )[0].status_code
        == 302
    )
    assert case["lead_client"].post(url, data).status_code == 302
    assert (
        post(case["lead_client"], "report-resubmit", report, REPORT_NARRATIVE)[
            0
        ].status_code
        == 302
    )
    report.refresh_from_db()
    assert report.revision == 2 and report.snapshot["total_amount"] == "3600.00"
    assert WeeklyReportLine.objects.get(report=report, revision=1).amount == Decimal(
        "3500.00"
    )
    assert WeeklyReportLine.objects.get(report=report, revision=2).amount == Decimal(
        "3600.00"
    )
    assert (
        report.snapshot_hash
        == hashlib.sha256(canonical_json(report.snapshot).encode()).hexdigest()
    )


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE weekly_reports SET review_comment = 'tampered' WHERE id = %s",
        "DELETE FROM weekly_reports WHERE id = %s",
        "UPDATE weekly_report_lines SET amount = 1 WHERE report_id = %s",
        "DELETE FROM weekly_report_lines WHERE report_id = %s",
    ],
)
def test_t_rpt_locked_immutable(acceptance_setup, statement):
    case = acceptance_setup
    submit(case)
    assert (
        post(
            case["reviewer_client"],
            "report-approve",
            case["report"],
            {"expected_revision": 1},
        )[0].status_code
        == 302
    )
    with pytest.raises(DatabaseError, match="locked"), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(statement, [case["report"].pk])


@pytest.mark.django_db(transaction=True)
def test_t_rpt_concurrent_review(acceptance_setup):
    case = acceptance_setup
    submit(case)
    barrier = Barrier(2)

    def approve(_index):
        try:
            barrier.wait(timeout=10)
            try:
                report_services.transition(
                    case["reviewer"], case["report"], "approve", expected_revision=1
                )
                return "locked"
            except InvalidTransition:
                return "conflict"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(approve, range(2)))
    assert sorted(results) == ["conflict", "locked"]
    assert (
        AuditLog.objects.filter(
            action="report.approved", entity_id=case["report"].pk
        ).count()
        == 1
    )
    assert (
        AuditLog.objects.filter(
            action="report.locked", entity_id=case["report"].pk
        ).count()
        == 1
    )


def test_t_col_week_closed_create_and_void(acceptance_setup, branch):
    case = acceptance_setup
    submit(case)
    response = case["lead_client"].post(
        reverse("collection-create", kwargs={"branch_pk": branch.pk}),
        {
            "collection_date": date(2026, 10, 25),
            "amount": "100.00",
            "method": "CASH",
            "receipt_no": "R-NEW",
        },
    )
    assert response.status_code == 409 and "week is closed" in response.text
    response = case["lead_client"].post(
        reverse("collection-void", args=[case["item"].pk]),
        {"reason": "A correction is needed"},
    )
    assert response.status_code == 409 and "week is closed" in response.text
    case["item"].refresh_from_db()
    assert case["item"].voided_at is None


@pytest.mark.parametrize(
    "status", [ReportStatus.SUBMITTED, ReportStatus.RETURNED, ReportStatus.RESUBMITTED]
)
def test_branch_close_blocked_by_open_report(acceptance_setup, bl, branch, status):
    case = acceptance_setup
    services.create_transfer(
        bl, branch, [case["item"].pk], business_clock.today(), "BANK-REPORTED"
    )
    submit(case)
    if status in {ReportStatus.RETURNED, ReportStatus.RESUBMITTED}:
        post(
            case["reviewer_client"],
            "report-return",
            case["report"],
            {"expected_revision": 1, "comment": "Please check details"},
        )
    if status == ReportStatus.RESUBMITTED:
        post(case["lead_client"], "report-resubmit", case["report"], REPORT_NARRATIVE)
    admin = User.objects.create_user(
        email="report-close-admin@example.com",
        full_name="Report admin",
        role=Role.SUPER_ADMIN,
    )
    client = Client()
    client.force_login(admin)
    response = client.post(
        reverse("branch-transition", kwargs={"pk": branch.pk, "action": "close"}),
        {"reason": "Closing this branch"},
    )
    assert response.status_code == 409 and "Open weekly reports" in response.text
