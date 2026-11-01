"""Startup drafts missing weeks without changing authored report history."""

from datetime import date, timedelta
from io import StringIO

import pytest
from django.conf import settings as django_settings
from django.core.management import call_command

from apps.audit.models import AuditLog
from apps.branches.models import Branch, BranchStatus
from apps.finance.models import ReportStatus, WeeklyReport
from apps.finance.report_selectors import week_bounds

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("demo_mode", [True, False])
def test_t_rpt_autodraft_startup_after_seed(settings, clock, demo_mode):
    clock.move_to("2026-10-31T23:00:00+05:00")
    settings.DEMO_MODE = demo_mode
    if not demo_mode:
        # Non-demo startup must fill gaps in previously imported branch history too.
        call_command(
            "import_sample_data",
            str(django_settings.BASE_DIR / "sample_data"),
            stdout=StringIO(),
        )
    output = StringIO()
    call_command("startup", stdout=output)
    current_week = date(2026, 10, 26)
    for branch in Branch.objects.filter(status=BranchStatus.ACTIVE):
        week = week_bounds(branch.opened_on)[0]
        expected = []
        while week <= current_week:
            expected.append(week)
            week += timedelta(days=7)
        assert (
            list(
                WeeklyReport.objects.filter(branch=branch)
                .order_by("week_start")
                .values_list("week_start", flat=True)
            )
            == expected
        )
        assert (
            WeeklyReport.objects.get(branch=branch, week_start=current_week).status
            == ReportStatus.DRAFT
        )

    # Historical reports survive, but inactive branches receive no extra weeks.
    assert WeeklyReport.objects.filter(branch__status=BranchStatus.PAUSED).count() == 1
    assert WeeklyReport.objects.filter(branch__status=BranchStatus.CLOSED).count() == 1
    assert not WeeklyReport.objects.filter(branch__status=BranchStatus.FORMING).exists()
    assert set(
        AuditLog.objects.filter(action="report.drafted").values_list(
            "actor_label", flat=True
        )
    ) == {"system"}
    assert "Created 20 weekly report drafts." in output.getvalue()

    report_count = WeeklyReport.objects.count()
    event_count = AuditLog.objects.filter(action="report.drafted").count()
    second = StringIO()
    call_command("startup", stdout=second)
    assert WeeklyReport.objects.count() == report_count
    assert AuditLog.objects.filter(action="report.drafted").count() == event_count
    assert "Created 0 weekly report drafts." in second.getvalue()


def test_t_rpt_autodraft_command_counts_only_new_rows(clock):
    clock.move_to("2026-10-31T23:00:00+05:00")
    call_command("seed_demo", stdout=StringIO())
    existing = set(WeeklyReport.objects.values_list("pk", flat=True))
    output = StringIO()
    call_command("generate_weekly_drafts", stdout=output)
    created = WeeklyReport.objects.exclude(pk__in=existing)
    assert created.count() == 20
    assert output.getvalue() == "Created 20 weekly report drafts.\n"
    assert set(created.values_list("branch__status", flat=True)) == {
        BranchStatus.ACTIVE
    }
    assert not created.exclude(status=ReportStatus.DRAFT).exists()
    assert (
        AuditLog.objects.filter(
            action="report.drafted", entity_id__in=created.values("pk")
        ).count()
        == 20
    )


def test_t_rpt_autodraft_empty_non_demo_startup(settings, clock):
    clock.move_to("2026-10-31T23:00:00+05:00")
    settings.DEMO_MODE = False
    output = StringIO()
    call_command("startup", stdout=output)
    assert not WeeklyReport.objects.exists()
    assert not AuditLog.objects.filter(action="report.drafted").exists()
    assert "Created 0 weekly report drafts." in output.getvalue()
