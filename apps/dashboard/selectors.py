"""Compose dashboard reads without repeating additive per-branch aggregates."""

from django.db.models import Count, Q

from apps.branches.models import BranchStatus
from apps.dashboard import kpis
from apps.volunteers.models import ApplicationStatus


def dashboard_data(period, as_of, branch_ids=None, *, head_office=False):
    """Reuse L2's grouped sums so total query count does not grow with branches."""
    branches = kpis.l2(period, as_of, branch_ids)
    collected = sum((row["collected"] for row in branches), kpis.ZERO)
    approved = sum((row["approved"] for row in branches), kpis.ZERO)
    data = {
        "collected": {
            "amount": collected,
            "count": sum(row["collected_count"] for row in branches),
        },
        "approved": approved,
        "awaiting": collected - approved,
        "unsent": {
            "amount": sum((row["unsent"] for row in branches), kpis.ZERO),
            "count": sum(row["unsent_count"] for row in branches),
            "oldest_age": max((row["oldest_age"] for row in branches), default=0),
        },
        "members": kpis.k6(period, as_of, branch_ids),
        "reports": kpis.k8(period, as_of, branch_ids),
        "sent": kpis.k10(period, as_of, branch_ids),
        "money_trend": kpis.tr1(period, as_of, branch_ids),
        "unsent_rows": kpis.l1(period, as_of, branch_ids),
    }
    if head_office:
        statuses = dict.fromkeys(BranchStatus.values, 0)
        for row in branches:
            statuses[row["branch_status"]] += 1
        statuses["total"] = len(branches)
        data.update(
            branch_rows=branches,
            branches=statuses,
            applications=kpis.k7(period, as_of),
            compliance=kpis.k9(period, as_of),
            member_trend=kpis.tr2(period, as_of),
        )
    return data


def hr_data(period, as_of, branch_ids):
    """Return assigned-branch pipeline counts without any finance records."""
    branches = (
        kpis._branches(as_of, branch_ids)
        .annotate(
            pending=Count(
                "applications",
                filter=Q(
                    applications__status=ApplicationStatus.PENDING,
                    applications__created_at__lte=as_of,
                ),
            )
        )
        .order_by("code")
    )
    return {
        "branch_rows": branches,
        "applications": kpis.k7(period, as_of, branch_ids),
        "members": kpis.k6(period, as_of, branch_ids),
    }
