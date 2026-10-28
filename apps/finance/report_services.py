"""Weekly report writes use explicit transactions and the existing audit chain."""

from datetime import timedelta

from django.db import transaction

from apps import audit
from apps.branches.models import Branch, BranchStatus
from apps.core import clock
from apps.finance.models import WeeklyReport
from apps.finance.report_selectors import week_bounds


def ensure_drafts(branch):
    """Lazily create missing weeks once, with system audit events. BR-081, BR-082."""
    reports = []
    with transaction.atomic():
        branch = Branch.objects.select_for_update(no_key=True).get(pk=branch.pk)
        if branch.status != BranchStatus.ACTIVE or branch.opened_on is None:
            return reports
        week, _ = week_bounds(branch.opened_on)
        current, _ = week_bounds(clock.today())
        while week <= current:
            report, created = WeeklyReport.objects.get_or_create(
                branch=branch,
                week_start=week,
                defaults={
                    "week_end": week + timedelta(days=6),
                    "created_at": clock.now(),
                    "updated_at": clock.now(),
                },
            )
            if created:
                audit.record(
                    None,
                    "report.drafted",
                    entity=report,
                    branch_id=branch.pk,
                    after={
                        "status": report.status,
                        "week_start": report.week_start,
                        "week_end": report.week_end,
                        "revision": 0,
                    },
                )
            reports.append(report)
            week += timedelta(days=7)
    return reports
