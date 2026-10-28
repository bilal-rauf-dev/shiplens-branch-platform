from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.dashboard import kpis
from tests.dashboard.conftest import AS_OF

pytestmark = pytest.mark.django_db


def test_dashboard_reads_locked_current_revisions_and_scoped_receipts(sample_data):
    period = 2026, 10
    assert kpis.k1(period, AS_OF)["amount"] == Decimal("73250.50")
    assert kpis.k2(period, AS_OF) == Decimal("43250.50")
    assert [row["receipt_no"] for row in kpis.l1(period, AS_OF)] == [
        "C13",
        "C05",
        "C10",
        "C06",
        "C11",
        "C15",
    ]
    assert kpis.k9(period, AS_OF)["week_start"] == date(2026, 10, 19)


@pytest.mark.parametrize(
    "prefix,route",
    [
        ("superadmin", "dashboard-head-office"),
        ("finance", "dashboard-head-office"),
        ("branchlead", "dashboard-branch"),
        ("hr", "dashboard-hr"),
    ],
)
def test_dashboard_role_pages_and_chart_loading(sample_data, client, prefix, route):
    client.force_login(User.objects.get(email=f"{prefix}.demo@shiplens.test"))
    response = client.get(reverse(route))
    assert response.status_code == 200
    if prefix == "hr":
        assert "chart.umd.min.js" not in response.text
        assert "Collected" not in response.text
        assert response.context["applications"]["pending"] == 3
    else:
        assert "chart.umd.min.js" in response.text
        assert 'type="application/json"' in response.text
        assert "static/js/dashboard.js" in response.text
    assert "<script>" not in response.text


def test_dashboard_default_fallback_and_explicit_empty_month(
    sample_data, client, clock
):
    clock.move_to("2026-11-10T12:00:00+05:00")
    client.force_login(User.objects.get(role="SUPER_ADMIN"))
    response = client.get(reverse("dashboard-head-office"))
    assert "Showing October 2026 (latest month with data)" in response.text
    response = client.get(reverse("dashboard-head-office"), {"period": "2026-11"})
    assert response.context["collected"]["amount"] == Decimal("0.00")
    assert response.context["applications"]["rate"] is None
    assert "No collections in this period" in response.text
    assert (
        client.get(reverse("dashboard-head-office"), {"period": "wrong"}).status_code
        == 400
    )


def test_dashboard_public_pages_do_not_load_chart_javascript(client):
    assert "chart.umd.min.js" not in client.get(reverse("home")).text


def test_dashboard_urdu_renders_rtl_with_json_data(sample_data, client):
    client.force_login(User.objects.get(role="FINANCE_REVIEWER"))
    response = client.get("/ur/app/dashboard/")
    assert response.status_code == 200
    assert 'lang="ur" dir="rtl"' in response.text
    assert 'id="money-trend"' in response.text
