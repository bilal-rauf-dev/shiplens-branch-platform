"""Live report figures are pure reads; approved figures come from stored lines."""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
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
    figures = items.aggregate(
        total_amount=Sum("amount", default=Decimal("0.00")), entry_count=Count("pk")
    )
    by_method = {method: Decimal("0.00") for method in CollectionMethod.values}
    for row in items.order_by().values("method").annotate(total=Sum("amount")):
        by_method[row["method"]] = row["total"]
    figures["by_method"] = by_method
    figures["unsent_amount_at_week_end"] = items.filter(
        Q(transfer__isnull=True) | Q(transfer__transfer_date__gt=end)
    ).aggregate(total=Sum("amount", default=Decimal("0.00")))["total"]
    figures.update(
        Member.objects.filter(branch=branch).aggregate(
            new_members=Count("pk", filter=Q(joined_on__range=(start, end))),
            active_members_end=Count(
                "pk", filter=Q(status=MemberStatus.ACTIVE, joined_on__lte=end)
            ),
        )
    )
    lower = datetime.combine(start, time.min, tzinfo=clock.KARACHI)
    upper = datetime.combine(end, time.max, tzinfo=clock.KARACHI)
    figures.update(
        Application.objects.filter(preferred_branch=branch).aggregate(
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
    )
    return figures
