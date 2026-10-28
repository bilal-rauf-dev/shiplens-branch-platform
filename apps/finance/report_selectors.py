"""Live report figures are pure reads; approved figures come from stored lines."""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum

from apps.branches.models import Branch, BranchStatus
from apps.core import clock
from apps.finance.models import Collection, CollectionMethod
from apps.volunteers.models import Application, ApplicationStatus, Member, MemberStatus


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
