from datetime import date, timedelta

import polib
import pytest
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.finance import report_services
from apps.finance.models import WeeklyReport
from apps.finance.report_selectors import week_bounds
from tests.rbac.registry import REPORT_NARRATIVE

pytestmark = pytest.mark.django_db


def test_report_lazy_list_detail_and_post_errors(client, bl, branch, clock):
    clock.move_to("2026-10-26T10:00:00+05:00")
    branch.opened_on = date(2026, 10, 19)
    branch.save(update_fields=["opened_on"])
    client.force_login(bl)
    response = client.get(reverse("report-list"))
    assert response.status_code == 200 and response.context["paginator"].count == 2
    report = WeeklyReport.objects.get(branch=branch, week_start=date(2026, 10, 19))
    response = client.get(reverse("report-detail", args=[report.pk]))
    assert "Live figures" in response.text and "Pending" in response.text
    assert "Save narrative" in response.text and "History" in response.text
    assert (
        client.post(
            reverse("report-save", args=[report.pk]), {"activities": "short"}
        ).status_code
        == 400
    )
    response = client.post(reverse("report-save", args=[report.pk]), REPORT_NARRATIVE)
    assert response.status_code == 302
    assert "Report saved." in client.get(response.url).text
    response = client.post(reverse("report-submit", args=[report.pk]), REPORT_NARRATIVE)
    assert response.status_code == 302
    assert "Save narrative" not in client.get(response.url).text


def test_review_queue_oldest_first_and_returned_banner(client, bl, branch, clock):
    clock.move_to("2026-10-26T09:00:00+05:00")
    branch.opened_on = date(2026, 10, 12)
    branch.save(update_fields=["opened_on"])
    reports = report_services.ensure_drafts(branch)
    report_services.transition(bl, reports[0], "submit", narrative=REPORT_NARRATIVE)
    clock.shift(3600)
    report_services.transition(bl, reports[1], "submit", narrative=REPORT_NARRATIVE)
    reviewer = User.objects.create_user(
        email="queue-reviewer@example.com",
        full_name="Queue reviewer",
        role=Role.FINANCE_REVIEWER,
    )
    client.force_login(reviewer)
    response = client.get(reverse("report-review-queue"))
    assert [item.pk for item in response.context["reports"]] == [
        reports[0].pk,
        reports[1].pk,
    ]
    detail = client.get(reverse("report-detail", args=[reports[0].pk]))
    assert (
        'name="expected_revision"' in detail.text and "Approve and lock" in detail.text
    )
    response = client.post(
        reverse("report-return", args=[reports[0].pk]),
        {"expected_revision": 1, "comment": "Please add the missing details"},
    )
    assert response.status_code == 302
    assert "Please add the missing details" in client.get(response.url).text


def test_report_list_filters_pagination_and_scope(client, bl, branch, branch_factory):
    start, _ = week_bounds(date(2026, 10, 25))
    WeeklyReport.objects.bulk_create(
        [
            WeeklyReport(
                branch=branch,
                week_start=start - timedelta(weeks=index),
                week_end=start - timedelta(weeks=index) + timedelta(days=6),
            )
            for index in range(30)
        ]
    )
    other = branch_factory(code="BR-LHE-01")
    foreign = WeeklyReport.objects.create(
        branch=other, week_start=start, week_end=start + timedelta(days=6)
    )
    client.force_login(bl)
    params = {
        "branch": str(branch.pk),
        "status": "DRAFT",
        "week_from": "2025-01-01",
        "week_to": "2026-10-25",
    }
    response = client.get(reverse("report-list"), params)
    assert (
        len(response.context["reports"]) == 25
        and response.context["paginator"].count == 30
    )
    assert "week_from=2025-01-01" in response.text and "page=2" in response.text
    assert client.get(reverse("report-detail", args=[foreign.pk])).status_code == 404
    assert (
        client.post(
            reverse("report-submit", args=[foreign.pk]), REPORT_NARRATIVE
        ).status_code
        == 404
    )
    response = client.get(reverse("report-list"), {"branch": other.pk})
    assert response.context["filter_form"].errors and not response.context["reports"]


def test_report_urdu_wrapped_strings(client, bl, branch, settings, tmp_path):
    compiled = tmp_path / "ur/LC_MESSAGES/django.mo"
    compiled.parent.mkdir(parents=True)
    polib.pofile(
        str(settings.BASE_DIR / "locale/ur/LC_MESSAGES/django.po")
    ).save_as_mofile(str(compiled))
    settings.LOCALE_PATHS = [tmp_path]
    client.force_login(bl)
    response = client.get("/ur/app/reports/")
    assert (
        response.status_code == 200
        and 'dir="rtl"' in response.text
        and "ہفتہ وار رپورٹیں" in response.text
    )
