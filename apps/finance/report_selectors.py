"""Live report figures are pure reads; approved figures come from stored lines."""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, OuterRef, Q, Subquery, Sum
from django.db.models.functions import JSONObject
from django.utils.translation import gettext_lazy as _

from apps.accounts.permissions import can, scope_queryset
from apps.audit.models import AuditLog
from apps.branches.models import Branch, BranchStatus
from apps.core import clock
from apps.finance.models import Collection, CollectionMethod, ReportStatus, WeeklyReport
from apps.finance.report_fields import REPORT_FIELDS
from apps.volunteers.models import Application, ApplicationStatus, Member, MemberStatus


def reports():
    return WeeklyReport.objects.select_related(
        "branch", "submitted_by", "reviewed_by", "approved_by"
    ).order_by("-week_start", "-pk")


def draft_branches(user):
    return scope_queryset(
        user, "report.list", active_report_branches(), branch_field="pk"
    )


def filter_reports(queryset, params):
    if params.get("branch"):
        queryset = queryset.filter(branch=params["branch"])
    if params.get("status"):
        queryset = queryset.filter(status=params["status"])
    if params.get("week_from"):
        queryset = queryset.filter(week_start__gte=params["week_from"])
    if params.get("week_to"):
        queryset = queryset.filter(week_start__lte=params["week_to"])
    return queryset


def detail_data(user, report):
    """Show live drafts, frozen submissions and the report's scoped audit history."""
    live = report.status in {ReportStatus.DRAFT, ReportStatus.RETURNED}
    figures = (
        report_aggregates(report.branch, report.week_start) if live else report.snapshot
    )
    source = (
        week_collections(report.branch, report.week_start)
        if live
        else report.lines.filter(revision=report.revision).order_by(
            "collection_date", "pk"
        )
    )
    labels = dict(CollectionMethod.choices)
    lines = [
        {
            "collection_id": row.pk if live else row.collection_id,
            "reference": row.reference,
            "collection_date": row.collection_date,
            "method": labels.get(row.method, row.method),
            "amount": row.amount,
        }
        for row in source
    ]
    narrative = report.narrative if live else report.snapshot.get("narrative", {})
    show_history = can(user, "audit.entity_history", report)
    events = (
        AuditLog.objects.filter(
            entity_type="weeklyreport", entity_id=report.pk
        ).order_by("-occurred_at", "-pk")
        if show_history
        else []
    )
    action_labels = {
        "report.drafted": _("Report drafted"),
        "report.submitted": _("Report submitted"),
        "report.returned": _("Report returned"),
        "report.resubmitted": _("Report resubmitted"),
        "report.approved": _("Report approved"),
        "report.locked": _("Report locked"),
        "report.narrative_updated": _("Narrative updated"),
    }
    history = []
    field_labels = {
        "status": _("Status"),
        "revision": _("Revision"),
        "locked_at": _("Locked at"),
    }
    for event in events:
        changes = [
            {
                "field": field_labels[key],
                "before": event.before.get(key),
                "after": event.after.get(key),
            }
            for key in ("status", "revision", "locked_at")
            if key in event.after
        ]
        if event.metadata.get("comment"):
            changes.append(
                {
                    "field": _("Review comment"),
                    "before": None,
                    "after": event.metadata["comment"],
                }
            )
        history.append(
            {
                "event": event,
                "action_label": action_labels.get(event.action, event.action),
                "changes": changes,
            }
        )
    return {
        "figures": figures,
        "lines": lines,
        "live": live,
        "method_totals": [
            {
                "label": label,
                "amount": figures.get("by_method", {}).get(method, Decimal("0.00")),
            }
            for method, label in CollectionMethod.choices
        ],
        "narrative_items": [
            {"label": spec["label"], "value": narrative.get(name, "—")}
            for name, spec in REPORT_FIELDS.items()
        ],
        "history": history,
        "show_history": show_history,
    }


def week_bounds(value):
    """Use business dates or convert an aware timestamp to Karachi. BR-080."""
    if isinstance(value, datetime):
        if value.utcoffset() is None:
            raise ValueError("An aware timestamp is required")
        value = value.astimezone(clock.KARACHI).date()
    start = value - timedelta(days=value.weekday())
    return start, start + timedelta(days=6)


def active_report_branches():
    return Branch.objects.filter(status=BranchStatus.ACTIVE).order_by("pk")


def week_is_closed(branch, collection_date):
    start, _ = week_bounds(collection_date)
    return WeeklyReport.objects.filter(
        branch=branch,
        week_start=start,
        status__in=[
            ReportStatus.SUBMITTED,
            ReportStatus.RESUBMITTED,
            ReportStatus.APPROVED,
            ReportStatus.LOCKED,
        ],
    ).exists()


def open_report_count(branch):
    return WeeklyReport.objects.filter(
        branch=branch,
        status__in=[
            ReportStatus.SUBMITTED,
            ReportStatus.RESUBMITTED,
            ReportStatus.RETURNED,
        ],
    ).count()


def week_collections(branch, week_start):
    start, end = week_bounds(week_start)
    return Collection.objects.filter(
        branch=branch, collection_date__range=(start, end), voided_at__isnull=True
    ).order_by("collection_date", "pk")


def report_aggregates(branch, week_start):
    """BR-083: current non-voided money; active-member history is an approximation."""
    start, end = week_bounds(week_start)
    items = week_collections(branch, start)
    money_fields = {
        "total_amount": Sum("amount", default=Decimal("0.00")),
        "entry_count": Count("pk"),
        "unsent_amount_at_week_end": Sum(
            "amount",
            filter=Q(transfer__isnull=True) | Q(transfer__transfer_date__gt=end),
            default=Decimal("0.00"),
        ),
    }
    for method in CollectionMethod.values:
        money_fields[f"method_{method}"] = Sum(
            "amount", filter=Q(method=method), default=Decimal("0.00")
        )
    figures = items.aggregate(**money_fields)
    figures["by_method"] = {
        method: figures.pop(f"method_{method}") for method in CollectionMethod.values
    }
    # Independent grouped subqueries avoid a member × application join while
    # returning both counter sets in one round trip. Empty groups become zeros.
    members = (
        Member.objects.filter(branch_id=OuterRef("pk")).order_by().values("branch_id")
    )
    members = members.annotate(
        counts=JSONObject(
            new_members=Count("pk", filter=Q(joined_on__range=(start, end))),
            active_members_end=Count(
                "pk", filter=Q(status=MemberStatus.ACTIVE, joined_on__lte=end)
            ),
        )
    ).values("counts")
    lower = datetime.combine(start, time.min, tzinfo=clock.KARACHI)
    upper = datetime.combine(end, time.max, tzinfo=clock.KARACHI)
    applications = (
        Application.objects.filter(preferred_branch_id=OuterRef("pk"))
        .order_by()
        .values("preferred_branch_id")
    )
    applications = applications.annotate(
        counts=JSONObject(
            applications_received=Count(
                "pk", filter=Q(created_at__range=(lower, upper))
            ),
            applications_accepted=Count(
                "pk",
                filter=Q(
                    status=ApplicationStatus.ACCEPTED, decided_at__range=(lower, upper)
                ),
            ),
            applications_declined=Count(
                "pk",
                filter=Q(
                    status=ApplicationStatus.DECLINED, decided_at__range=(lower, upper)
                ),
            ),
        )
    ).values("counts")
    counts = (
        Branch.objects.annotate(
            member_counts=Subquery(members),
            application_counts=Subquery(applications),
        )
        .values("member_counts", "application_counts")
        .get(pk=branch.pk)
    )
    figures.update(
        counts["member_counts"] or {"new_members": 0, "active_members_end": 0}
    )
    figures.update(
        counts["application_counts"]
        or {
            "applications_received": 0,
            "applications_accepted": 0,
            "applications_declined": 0,
        }
    )
    return figures
