"""Acceptance criterion 1: every hand-calculated value in planning/09 §4."""

from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.models import Role, User, UserBranchAssignment
from apps.accounts.services import remove_branch_assignment
from apps.branches.models import Branch
from apps.core import clock as business_clock
from apps.dashboard import kpis
from apps.finance import report_services
from apps.finance import services as finance_services
from apps.finance.models import Collection, WeeklyReport
from apps.volunteers.models import Application
from tests.dashboard.conftest import AS_OF

pytestmark = pytest.mark.django_db
OCTOBER = (2026, 10)
D = Decimal


def test_t_dash_seed_october_reference_values(sample_data):
    """09 §4.1: one assertion for each scalar, with money as exact Decimal."""
    collected = kpis.k1(OCTOBER, AS_OF)
    assert collected["amount"] == D("73250.50"), "K1 amount"
    assert collected["count"] == 8, "K1 count"
    assert kpis.k2(OCTOBER, AS_OF) == D("43250.50"), "K2 approved"
    assert kpis.k3(OCTOBER, AS_OF) == D("30000.00"), "K3 awaiting"
    unsent = kpis.k4(OCTOBER, AS_OF)
    assert unsent["amount"] == D("35250.50"), "K4 amount"
    assert unsent["count"] == 6, "K4 count"
    assert unsent["oldest_age"] == 26, "K4 oldest age"
    branches = kpis.k5(OCTOBER, AS_OF)
    assert branches["ACTIVE"] == 2, "K5 active"
    assert branches["PAUSED"] == 1, "K5 paused"
    assert branches["FORMING"] == 1, "K5 forming"
    assert branches["CLOSED"] == 1, "K5 closed"
    assert branches["total"] == 5, "K5 total"
    members = kpis.k6(OCTOBER, AS_OF)
    assert members["active"] == 9, "K6 active"
    assert members["new"] == 3, "K6 new"
    applications = kpis.k7(OCTOBER, AS_OF)
    assert applications["pending"] == 3, "K7 pending"
    assert applications["rate"] == D("75"), "K7 acceptance rate"
    assert applications["accepted"] == 3, "K7 October accepted decisions"
    assert applications["declined"] == 1, "K7 October declined decisions"
    reports = kpis.k8(OCTOBER, AS_OF)
    assert reports["awaiting"] == 1, "K8 awaiting"
    assert reports["returned"] == 1, "K8 returned"
    compliance = kpis.k9(OCTOBER, AS_OF)
    assert compliance["week_start"] == date(2026, 10, 19), "K9 completed week"
    assert compliance["submitted"] == 0, "K9 compliant branches"
    assert compliance["active"] == 2, "K9 denominator"
    assert compliance["rate"] == D("0"), "K9 percentage"
    assert kpis.k10(OCTOBER, AS_OF) == D("38000.00"), "K10 sent"


@pytest.mark.parametrize(
    "code,collected,approved,unsent,count,status,week",
    [
        ("BR-KHI-01", "37750.50", "25250.50", "17750.50", 3, "DRAFT", "2026-10-19"),
        ("BR-LHE-01", "33000.00", "18000.00", "15000.00", 2, "SUBMITTED", "2026-10-12"),
        ("BR-ISB-01", "2500.00", "0.00", "2500.00", 1, "LOCKED", "2026-08-31"),
        ("BR-PEW-01", "0.00", "0.00", "0.00", 0, None, None),
        ("BR-QTA-01", "0.00", "0.00", "0.00", 0, "LOCKED", "2026-08-10"),
    ],
    ids=["KHI", "LHE", "ISB", "PEW", "QTA"],
)
def test_t_dash_seed_l2_per_branch(
    sample_data, code, collected, approved, unsent, count, status, week
):
    row = next(row for row in kpis.l2(OCTOBER, AS_OF) if row["branch_code"] == code)
    assert row["collected"] == D(collected), f"L2 {code} collected"
    assert row["approved"] == D(approved), f"L2 {code} approved"
    assert row["unsent"] == D(unsent), f"L2 {code} unsent"
    assert row["unsent_count"] == count, f"L2 {code} unsent count"
    if status is None:
        assert row["latest_report"] is None, f"L2 {code} no report"
    else:
        assert row["latest_report"]["status"] == status, f"L2 {code} latest status"
        assert row["latest_report"]["week_start"] == date.fromisoformat(week), (
            f"L2 {code} latest week"
        )


def test_t_dash_seed_l2_totals(sample_data):
    rows = kpis.l2(OCTOBER, AS_OF)
    assert sum(row["collected"] for row in rows) == D("73250.50"), "L2 total collected"
    assert sum(row["approved"] for row in rows) == D("43250.50"), "L2 total approved"
    assert sum(row["unsent"] for row in rows) == D("35250.50"), "L2 total unsent"
    assert sum(row["unsent_count"] for row in rows) == 6, "L2 total unsent count"


@pytest.mark.parametrize(
    "period,collected,approved,awaiting,sent,new,rate",
    [
        ((2026, 7), "0.00", "0.00", "0.00", "0.00", 1, None),
        ((2026, 8), "10000.00", "10000.00", "0.00", "10000.00", 5, None),
        ((2026, 9), "71500.00", "71500.00", "0.00", "71500.00", 3, "0"),
        ((2026, 10), "73250.50", "43250.50", "30000.00", "38000.00", 3, "75"),
        ((2026, 11), "0.00", "0.00", "0.00", "0.00", 0, None),
    ],
    ids=["July-no-money", "August", "September", "October", "November-empty"],
)
def test_t_dash_seed_other_periods(
    sample_data, period, collected, approved, awaiting, sent, new, rate
):
    assert kpis.k1(period, AS_OF)["amount"] == D(collected), f"{period} K1"
    assert kpis.k2(period, AS_OF) == D(approved), f"{period} K2"
    assert kpis.k3(period, AS_OF) == D(awaiting), f"{period} K3"
    assert kpis.k10(period, AS_OF) == D(sent), f"{period} K10"
    assert kpis.k6(period, AS_OF)["new"] == new, f"{period} K6 new"
    assert kpis.k7(period, AS_OF)["rate"] == (D(rate) if rate is not None else None), (
        f"{period} K7 rate"
    )


def test_t_dash_seed_all_time_balance(sample_data):
    collected = sum(kpis.k1((2026, month), AS_OF)["amount"] for month in range(7, 12))
    sent = sum(kpis.k10((2026, month), AS_OF) for month in range(7, 12))
    unsent = kpis.k4(OCTOBER, AS_OF)["amount"]
    assert collected == D("154750.50"), "All-time collected"
    assert sent == D("119500.00"), "All-time sent"
    assert unsent == D("35250.50"), "All-time unsent"
    assert sent + unsent == D("154750.50"), "Sent plus unsent equals collected"


def test_t_dash_trends(sample_data):
    expected_months = [date(2025, 11, 1), date(2025, 12, 1)] + [
        date(2026, month, 1) for month in range(1, 11)
    ]
    money = kpis.tr1(OCTOBER, AS_OF)
    members = kpis.tr2(OCTOBER, AS_OF)
    assert len(money) == 12, "TR1 point count"
    assert len(members) == 12, "TR2 point count"
    collected = ["0.00"] * 9 + ["10000.00", "71500.00", "73250.50"]
    approved = ["0.00"] * 9 + ["10000.00", "71500.00", "43250.50"]
    new = [0] * 8 + [1, 5, 3, 3]
    for index, month in enumerate(expected_months):
        assert money[index]["month"] == month, f"TR1 month {index}"
        assert money[index]["collected"] == D(collected[index]), (
            f"TR1 {month} collected"
        )
        assert money[index]["approved"] == D(approved[index]), f"TR1 {month} approved"
        assert members[index]["month"] == month, f"TR2 month {index}"
        assert members[index]["new"] == new[index], f"TR2 {month} new"


@pytest.mark.parametrize(
    "index,branch,receipt,day,method,amount,age,status",
    [
        (0, "BR-ISB-01", "C13", "2026-10-05", "CASH", "2500.00", 26, None),
        (1, "BR-KHI-01", "C05", "2026-10-08", "BANK_DEPOSIT", "5250.50", 23, "LOCKED"),
        (2, "BR-LHE-01", "C10", "2026-10-13", "CASH", "11000.00", 18, "SUBMITTED"),
        (3, "BR-KHI-01", "C06", "2026-10-14", "CASH", "9000.00", 17, "RETURNED"),
        (4, "BR-LHE-01", "C11", "2026-10-15", "CHEQUE", "4000.00", 16, "SUBMITTED"),
        (5, "BR-KHI-01", "C15", "2026-10-21", "CASH", "3500.00", 10, "DRAFT"),
    ],
    ids=["C13", "C05", "C10", "C06", "C11", "C15"],
)
def test_t_dash_seed_l1_unsent_rows(
    sample_data, index, branch, receipt, day, method, amount, age, status
):
    rows = kpis.l1(OCTOBER, AS_OF)
    assert len(rows) == 6, "L1 row count"
    row = rows[index]
    assert row["branch_code"] == branch, f"L1 {receipt} branch"
    assert row["receipt_no"] == receipt, f"L1 {receipt} order"
    assert row["date"] == date.fromisoformat(day), f"L1 {receipt} date"
    assert row["method"] == method, f"L1 {receipt} method"
    assert row["amount"] == D(amount), f"L1 {receipt} amount"
    assert row["age"] == age, f"L1 {receipt} age"
    assert row["locked"] is True, f"L1 {receipt} lock"
    assert row["report_status"] == status, f"L1 {receipt} report status"


def test_t_dash_seed_edge_cases(sample_data):
    receipts = {row["receipt_no"]: row for row in kpis.l1(OCTOBER, AS_OF)}
    assert receipts["C05"]["report_status"] == "LOCKED", "Locked but unsent C05"
    assert receipts["C06"]["report_status"] == "RETURNED", (
        "Returned R8 money is pending"
    )
    assert Branch.objects.get(code="BR-ISB-01").status == "PAUSED", "ISB paused"
    assert Branch.objects.get(code="BR-QTA-01").status == "CLOSED", "QTA closed"
    assert "C07" not in receipts, "Voided C07 excluded from L1"
    assert Collection.objects.get(receipt_no="C07").voided_at is not None, (
        "C07 retained"
    )
    assert Application.objects.get(reference="APP-2026-00008").possible_duplicate, (
        "APP-00008 duplicate flag"
    )
    assert Collection.objects.get(receipt_no="C15").lock_at == AS_OF.replace(
        day=28, hour=18, minute=0
    ), "C15 exact lock instant"
    r5 = WeeklyReport.objects.get(branch__code="BR-KHI-01", week_start="2026-09-21")
    assert r5.revision == 2, "R5 revision"
    assert r5.lines.filter(revision=1).count() == 1, "R5 previous revision retained"
    assert kpis.k2((2026, 9), AS_OF) == D("71500.00"), "R5 counted once in September"
    r6 = WeeklyReport.objects.get(branch__code="BR-LHE-01", week_start="2026-09-28")
    assert r6.week_end == date(2026, 10, 4), "R6 spans two months"
    assert r6.lines.get(revision=r6.revision).collection_date == date(2026, 10, 2), (
        "R6 October line date"
    )


def test_t_dash_seed_previous_completed_week_compliance(sample_data):
    result = kpis.k9(OCTOBER, AS_OF.replace(day=24))
    assert result["week_start"] == date(2026, 10, 12), "Previous reference week"
    assert result["rate"] == D("50"), "Previous reference compliance"


def test_t_dash_seed_branch_lead_khi(sample_data):
    scope = [Branch.objects.get(code="BR-KHI-01").pk]
    assert kpis.k1(OCTOBER, AS_OF, scope)["amount"] == D("37750.50"), "KHI collected"
    assert kpis.k2(OCTOBER, AS_OF, scope) == D("25250.50"), "KHI approved"
    assert kpis.k3(OCTOBER, AS_OF, scope) == D("12500.00"), "KHI awaiting"
    assert kpis.k4(OCTOBER, AS_OF, scope)["amount"] == D("17750.50"), "KHI unsent"
    assert kpis.k4(OCTOBER, AS_OF, scope)["count"] == 3, "KHI unsent count"
    assert kpis.k10(OCTOBER, AS_OF, scope) == D("20000.00"), "KHI sent"
    assert kpis.k6(OCTOBER, AS_OF, scope)["active"] == 4, "KHI active members"
    assert kpis.k8(OCTOBER, AS_OF, scope)["returned"] == 1, "KHI returned reports"


def test_t_dash_realtime(sample_data, client):
    reviewer = User.objects.get(role=Role.FINANCE_REVIEWER)
    report = WeeklyReport.objects.get(branch__code="BR-LHE-01", week_start="2026-10-12")
    report_services.transition(reviewer, report, "approve", expected_revision=1)
    assert kpis.k2(OCTOBER, AS_OF) == D("58250.50"), "Realtime K2"
    assert kpis.k3(OCTOBER, AS_OF) == D("15000.00"), "Realtime K3"
    assert kpis.k8(OCTOBER, AS_OF)["awaiting"] == 0, "Realtime K8"
    client.force_login(reviewer)
    response = client.get(reverse("dashboard-head-office"))
    assert response.context["approved"] == D("58250.50"), "Realtime rendered approval"
    assert response.context["awaiting"] == D("15000.00"), "Realtime rendered pending"
    assert response.context["reports"]["awaiting"] == 0, "Realtime rendered queue"


def test_default_period_uses_october_in_november(sample_data, clock):
    clock.move_to("2026-11-10T12:00:00+05:00")
    assert kpis.default_period(business_clock.now()) == OCTOBER


def test_t_rbac_scope_dash(sample_data, client):
    client.force_login(User.objects.get(email="branchlead.demo@shiplens.test"))
    response = client.get(reverse("dashboard-branch"))
    assert response.context["collected"]["amount"] == D("37750.50")
    assert "BR-LHE-01" not in response.text
    assert "BR-ISB-01" not in response.text
    admin = User.objects.get(role=Role.SUPER_ADMIN)
    hr = User.objects.get(role=Role.HR_LEAD)
    for branch in Branch.objects.filter(code__in=["BR-LHE-01", "BR-ISB-01"]):
        remove_branch_assignment(admin, hr, branch.pk)
    client.force_login(hr)
    response = client.get(reverse("dashboard-hr"))
    assert response.context["applications"]["pending"] == 2
    assert response.context["members"]["active"] == 4
    assert "BR-LHE-01" not in response.text
    assert "BR-ISB-01" not in response.text
    assert client.get(reverse("dashboard-head-office")).status_code == 403
    client.force_login(User.objects.get(role=Role.FINANCE_REVIEWER))
    response = client.get(reverse("dashboard-head-office"))
    assert "Hamza Siddiqui" not in response.text
    assert "hamza.siddiqui@example.org" not in response.text


def test_t_growth_n_branches(sample_data, client, branch_factory):
    admin = User.objects.get(role=Role.SUPER_ADMIN)
    lead = User.objects.create_user(
        email="growth@example.org", full_name="Growth Lead", role=Role.BRANCH_LEAD
    )
    branches = [
        branch_factory(
            code=f"BR-GRW-{number:02d}",
            name_en=f"Growth branch {number}",
            status="ACTIVE",
            opened_on=AS_OF.date(),
        )
        for number in range(1, 51)
    ]
    UserBranchAssignment.objects.bulk_create(
        [
            UserBranchAssignment(user=lead, branch=branch, created_by=admin)
            for branch in branches
        ]
    )
    for branch in branches:
        for number, amount in enumerate(["100.00", "200.00", "300.00"], 1):
            finance_services.create_collection(
                lead,
                branch,
                {
                    "collection_date": AS_OF.date(),
                    "amount": D(amount),
                    "method": "CASH",
                    "receipt_no": f"GROWTH-{number}",
                },
            )
    scope = [branch.pk for branch in branches]
    assert kpis.k1(OCTOBER, AS_OF, scope)["amount"] == D("30000.00")
    assert kpis.k1(OCTOBER, AS_OF, scope)["count"] == 150
    assert kpis.k4(OCTOBER, AS_OF, scope)["amount"] == D("30000.00")
    client.force_login(admin)
    with CaptureQueriesContext(connection) as queries:
        response = client.get(reverse("dashboard-head-office"), {"period": "2026-10"})
    assert response.status_code == 200
    assert response.context["collected"]["amount"] == D("103250.50")
    assert len(response.context["branch_rows"]) == 55
    assert len(queries) <= 25, f"Dashboard executed {len(queries)} queries"
    print(f"50 added branches / 150 collections: dashboard used {len(queries)} queries")
