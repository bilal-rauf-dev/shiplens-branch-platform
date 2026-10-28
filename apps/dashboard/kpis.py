"""Uncached read-only KPI functions from planning/09 §2; money stays Decimal."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, F, Min, Q, Sum
from django.db.models.functions import TruncMonth

from apps.branches.models import Branch, BranchStatus
from apps.core import clock, rules
from apps.finance.models import (
    Collection,
    ReportStatus,
    Transfer,
    WeeklyReport,
    WeeklyReportLine,
)
from apps.finance.report_selectors import week_bounds
from apps.volunteers.models import Application, ApplicationStatus, Member, MemberStatus

ZERO = Decimal("0.00")
REVIEWABLE = [ReportStatus.SUBMITTED, ReportStatus.RESUBMITTED]
COMPLIANT = [*REVIEWABLE, ReportStatus.APPROVED, ReportStatus.LOCKED]


def month_bounds(period):
    year, month = period
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def _scope(queryset, branch_ids, field="branch_id"):
    return (
        queryset
        if branch_ids is None
        else queryset.filter(**{f"{field}__in": branch_ids})
    )


def _collections(as_of, branch_ids):
    return _scope(
        Collection.objects.filter(voided_at__isnull=True, created_at__lte=as_of),
        branch_ids,
    )


def _lines(as_of, branch_ids):
    return _scope(
        WeeklyReportLine.objects.filter(
            report__status=ReportStatus.LOCKED,
            revision=F("report__revision"),
            report__locked_at__lte=as_of,
        ),
        branch_ids,
        "report__branch_id",
    )


def _period(queryset, period, field):
    start, end = month_bounds(period)
    return queryset.filter(**{f"{field}__gte": start, f"{field}__lt": end})


def _branches(as_of, branch_ids):
    return _scope(Branch.objects.filter(created_at__lte=as_of), branch_ids, "pk")


def _percentage(numerator, denominator):
    return Decimal(numerator) * 100 / denominator if denominator else None


def default_period(as_of):
    """Use this month when populated, otherwise the latest populated month. A-27."""
    current = as_of.astimezone(clock.KARACHI).date()
    period = current.year, current.month
    entries = _collections(as_of, None)
    if _period(entries, period, "collection_date").exists():
        return period
    latest = (
        entries.order_by("-collection_date")
        .values_list("collection_date", flat=True)
        .first()
    )
    return (latest.year, latest.month) if latest else period


def k1(period, as_of, branch_ids=None):
    """Collected in the month, excluding voided receipts (K1)."""
    return _period(
        _collections(as_of, branch_ids), period, "collection_date"
    ).aggregate(amount=Sum("amount", default=ZERO), count=Count("pk"))


def k2(period, as_of, branch_ids=None):
    """Approved money by line date, only from the locked current revision (K2)."""
    return _period(_lines(as_of, branch_ids), period, "collection_date").aggregate(
        amount=Sum("amount", default=ZERO)
    )["amount"]


def k3(period, as_of, branch_ids=None):
    """Collected money still awaiting approval in the selected month (K3)."""
    return k1(period, as_of, branch_ids)["amount"] - k2(period, as_of, branch_ids)


def k4(period, as_of, branch_ids=None):
    """All-time unsent amount, receipt count and oldest age at as_of (K4)."""
    result = (
        _collections(as_of, branch_ids)
        .filter(transfer_id__isnull=True)
        .aggregate(
            amount=Sum("amount", default=ZERO),
            count=Count("pk"),
            oldest=Min("collection_date"),
        )
    )
    oldest = result.pop("oldest")
    result["oldest_age"] = (
        (as_of.astimezone(clock.KARACHI).date() - oldest).days if oldest else 0
    )
    return result


def k5(period, as_of, branch_ids=None):
    """Branch counts, including closed branches in the total (K5)."""
    result = dict.fromkeys(BranchStatus.values, 0)
    for row in (
        _branches(as_of, branch_ids).values("status").annotate(count=Count("pk"))
    ):
        result[row["status"]] = row["count"]
    result["total"] = sum(result.values())
    return result


def k6(period, as_of, branch_ids=None):
    """Active members now and new members by joined_on in the month (K6)."""
    start, end = month_bounds(period)
    return _scope(Member.objects.filter(created_at__lte=as_of), branch_ids).aggregate(
        active=Count("pk", filter=Q(status=MemberStatus.ACTIVE)),
        new=Count("pk", filter=Q(joined_on__gte=start, joined_on__lt=end)),
    )


def k7(period, as_of, branch_ids=None):
    """Pending applications and monthly decision acceptance percentage (K7)."""
    start, end = (
        datetime.combine(day, time.min, clock.KARACHI) for day in month_bounds(period)
    )
    decisions = Q(decided_at__gte=start, decided_at__lt=end, decided_at__lte=as_of)
    result = _scope(
        Application.objects.filter(created_at__lte=as_of),
        branch_ids,
        "preferred_branch_id",
    ).aggregate(
        pending=Count("pk", filter=Q(status=ApplicationStatus.PENDING)),
        accepted=Count("pk", filter=decisions & Q(status=ApplicationStatus.ACCEPTED)),
        declined=Count("pk", filter=decisions & Q(status=ApplicationStatus.DECLINED)),
    )
    result["rate"] = _percentage(
        result["accepted"], result["accepted"] + result["declined"]
    )
    return result


def k8(period, as_of, branch_ids=None):
    """Reports awaiting review and returned reports across all weeks (K8)."""
    return _scope(
        WeeklyReport.objects.filter(created_at__lte=as_of), branch_ids
    ).aggregate(
        awaiting=Count("pk", filter=Q(status__in=REVIEWABLE)),
        returned=Count("pk", filter=Q(status=ReportStatus.RETURNED)),
    )


def k9(period, as_of, branch_ids=None):
    """Active-branch compliance for the last fully completed PKT week (K9)."""
    week = week_bounds(as_of.astimezone(clock.KARACHI).date())[0] - timedelta(days=7)
    result = (
        _branches(as_of, branch_ids)
        .filter(status=BranchStatus.ACTIVE)
        .aggregate(
            active=Count("pk", distinct=True),
            submitted=Count(
                "pk",
                distinct=True,
                filter=Q(
                    weekly_reports__week_start=week,
                    weekly_reports__status__in=COMPLIANT,
                    weekly_reports__created_at__lte=as_of,
                ),
            ),
        )
    )
    result.update(
        rate=_percentage(result["submitted"], result["active"]), week_start=week
    )
    return result


def k10(period, as_of, branch_ids=None):
    """Transfers sent in the selected month, independently of report approval (K10)."""
    return _period(
        _scope(Transfer.objects.filter(created_at__lte=as_of), branch_ids),
        period,
        "transfer_date",
    ).aggregate(amount=Sum("total_amount", default=ZERO))["amount"]


def _months(period):
    year, month = period
    for offset in range(11, -1, -1):
        point_year, point_month = divmod(year * 12 + month - 1 - offset, 12)
        yield date(point_year, point_month + 1, 1)


def _monthly(queryset, field, months, *, value="amount", count=False):
    end = month_bounds((months[-1].year, months[-1].month))[1]
    aggregate = Count("pk") if count else Sum(value)
    rows = (
        queryset.filter(**{f"{field}__gte": months[0], f"{field}__lt": end})
        .annotate(month=TruncMonth(field))
        .values("month")
        .annotate(value=aggregate)
    )
    return {row["month"]: row["value"] for row in rows}


def tr1(period, as_of, branch_ids=None):
    """Twelve zero-filled collected/approved points ending at period (TR1)."""
    months = list(_months(period))
    collected = _monthly(_collections(as_of, branch_ids), "collection_date", months)
    approved = _monthly(_lines(as_of, branch_ids), "collection_date", months)
    return [
        {
            "month": month,
            "collected": collected.get(month, ZERO),
            "approved": approved.get(month, ZERO),
        }
        for month in months
    ]


def tr2(period, as_of, branch_ids=None):
    """Twelve zero-filled new-member counts by joining date (TR2)."""
    months = list(_months(period))
    members = _scope(Member.objects.filter(created_at__lte=as_of), branch_ids)
    counts = _monthly(members, "joined_on", months, count=True)
    return [{"month": month, "new": counts.get(month, 0)} for month in months]


def l1(period, as_of, branch_ids=None):
    """Oldest-first unsent receipts with their time/report lock state (L1)."""
    entries = list(
        _collections(as_of, branch_ids)
        .filter(transfer_id__isnull=True)
        .select_related("branch")
        .order_by("collection_date", "created_at", "pk")
    )
    reports = WeeklyReport.objects.filter(
        branch_id__in={item.branch_id for item in entries}, created_at__lte=as_of
    ).values("branch_id", "week_start", "status")
    statuses = {(row["branch_id"], row["week_start"]): row["status"] for row in reports}
    lock_days = rules.get("collection_lock_days")
    today = as_of.astimezone(clock.KARACHI).date()
    rows = []
    for item in entries:
        status = statuses.get((item.branch_id, week_bounds(item.collection_date)[0]))
        rows.append(
            {
                "collection_id": item.pk,
                "branch_code": item.branch.code,
                "reference": item.reference,
                "receipt_no": item.receipt_no,
                "date": item.collection_date,
                "method": item.method,
                "method_label": str(item.get_method_display()),
                "amount": item.amount,
                "age": (today - item.collection_date).days,
                "locked": as_of >= item.created_at + timedelta(days=lock_days)
                or status in COMPLIANT,
                "report_status": status,
                "report_label": str(ReportStatus(status).label) if status else None,
            }
        )
    return rows


def _group(queryset, **aggregates):
    return {
        row["branch_id"]: row
        for row in queryset.values("branch_id").annotate(**aggregates)
    }


def l2(period, as_of, branch_ids=None):
    """Per-branch money and latest report, using five grouped queries (L2)."""
    branches = list(_branches(as_of, branch_ids).order_by("code"))
    collected = _group(
        _period(_collections(as_of, branch_ids), period, "collection_date"),
        amount=Sum("amount"),
        count=Count("pk"),
    )
    approved = {
        row["report__branch_id"]: row["amount"]
        for row in _period(_lines(as_of, branch_ids), period, "collection_date")
        .values("report__branch_id")
        .annotate(amount=Sum("amount"))
    }
    unsent = _group(
        _collections(as_of, branch_ids).filter(transfer_id__isnull=True),
        amount=Sum("amount"),
        count=Count("pk"),
        oldest=Min("collection_date"),
    )
    latest = {}
    for report in (
        _scope(WeeklyReport.objects.filter(created_at__lte=as_of), branch_ids)
        .order_by("branch_id", "-week_start")
        .values("branch_id", "status", "id", "week_start")
    ):
        report["label"] = str(ReportStatus(report["status"]).label)
        latest.setdefault(report["branch_id"], report)
    today = as_of.astimezone(clock.KARACHI).date()
    rows = []
    for branch in branches:
        received = collected.get(branch.pk, {})
        outstanding = unsent.get(branch.pk, {})
        oldest = outstanding.get("oldest")
        rows.append(
            {
                "branch_id": branch.pk,
                "branch_code": branch.code,
                "branch_status": branch.status,
                "branch_status_label": str(branch.get_status_display()),
                "collected": received.get("amount", ZERO),
                "collected_count": received.get("count", 0),
                "approved": approved.get(branch.pk, ZERO),
                "unsent": outstanding.get("amount", ZERO),
                "unsent_count": outstanding.get("count", 0),
                "oldest_age": (today - oldest).days if oldest else 0,
                "latest_report": latest.get(branch.pk),
            }
        )
    return rows
