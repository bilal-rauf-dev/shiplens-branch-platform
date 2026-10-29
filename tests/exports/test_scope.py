from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

import pytest
from django.urls import reverse

from apps.accounts.models import Role, UserBranchAssignment
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.core.routes import ROUTE_ACTIONS
from apps.finance.models import WeeklyReport
from tests.exports.test_csv import download, sign_in
from tests.rbac.registry import ROUTE_CASES

pytestmark = pytest.mark.django_db
CSV_CODES = ["collections", "unsent", "reports", "summary", "members", "audit"]


def test_t_rbac_scope_exp(client, sample_data):
    sign_in(client, Role.BRANCH_LEAD)
    lahore = Branch.objects.get(code="BR-LHE-01")
    for branch_filter in [lahore.pk, "LHE"]:
        for code in ["collections", "unsent"]:
            _, rows = download(
                client, code, {"branch": branch_filter, "period": "2026-10"}
            )
            assert "BR-KHI-01" in str(rows)
            assert "BR-LHE-01" not in str(rows)
    report = WeeklyReport.objects.filter(branch=lahore).first()
    assert client.get(reverse("export-report-pdf", args=[report.pk])).status_code == 404
    assert not AuditLog.objects.filter(action="export.pdf").exists()


def test_finance_cannot_export_member_pii(client, sample_data):
    sign_in(client, Role.FINANCE_REVIEWER)
    count = AuditLog.objects.filter(action="export.csv").count()
    response = client.get(reverse("export-members-csv"))
    assert response.status_code == 403
    assert not response.streaming
    assert AuditLog.objects.filter(action="export.csv").count() == count


def test_hr_member_export_tracks_assignment_revocation(client, sample_data):
    user = sign_in(client, Role.HR_LEAD)
    UserBranchAssignment.objects.filter(user=user).exclude(
        branch__code="BR-KHI-01"
    ).delete()
    response, rows = download(client, "members", {"status": ""})
    assert {row[2] for row in rows[1:]} == {"BR-KHI-01"}
    assert "BR-KHI-01" in response["Content-Disposition"]
    UserBranchAssignment.objects.filter(user=user).delete()
    _, rows = download(client, "members", {"status": ""})
    assert len(rows) == 1


@pytest.mark.parametrize("code", CSV_CODES)
def test_csv_routes_deny_content_editor_and_redirect_anonymous(
    client, sample_data, code
):
    sign_in(client, Role.CONTENT_EDITOR)
    url = reverse(f"export-{code}-csv")
    assert client.get(url).status_code == 403
    client.logout()
    response = client.get(url)
    assert response.status_code == 302
    assert urlsplit(response.url).path == reverse("account-login")
    assert parse_qs(urlsplit(response.url).query) == {"next": [url]}


@pytest.mark.parametrize("name", ["export-report-pdf", "export-summary-pdf"])
def test_pdf_routes_deny_content_editor_and_redirect_anonymous(
    client, sample_data, name
):
    sign_in(client, Role.CONTENT_EDITOR)
    item = WeeklyReport.objects.first()
    url = reverse(name, args=[item.pk] if name == "export-report-pdf" else [])
    assert client.get(url).status_code == 403
    client.logout()
    assert client.get(url).status_code == 302


def test_every_export_has_a_get_matrix_recipe():
    exports = {name for name in ROUTE_ACTIONS if name.startswith("export-")}
    assert len(exports) == 8
    for name in exports:
        assert ROUTE_CASES[name].method == "GET"
        assert ROUTE_CASES[name].expected_success_status == 200


class Links(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.hrefs = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.append(dict(attrs).get("href", ""))


def test_export_buttons_preserve_current_filters(client, sample_data):
    sign_in(client, Role.SUPER_ADMIN)
    params = {"date_from": "2026-10-01", "method": "CASH", "state": "UNSENT"}
    response = client.get(reverse("collection-list"), params)
    href = next(
        href
        for href in Links(response.text).hrefs
        if "/exports/collections.csv" in href
    )
    assert parse_qs(urlsplit(href).query) == {
        key: [value] for key, value in params.items()
    }
    _, rows = download(client, "collections", params)
    assert len(rows) - 1 == response.context["totals"]["count"]


def test_branch_lead_has_no_member_export_button(client, sample_data):
    sign_in(client, Role.BRANCH_LEAD)
    response = client.get(reverse("member-list"))
    assert response.status_code == 200
    assert reverse("export-members-csv") not in Links(response.text).hrefs


def test_review_queue_has_no_unfiltered_report_export_link(client, sample_data):
    sign_in(client, Role.FINANCE_REVIEWER)
    response = client.get(reverse("report-review-queue"))
    assert response.status_code == 200
    assert not any(
        "/exports/reports.csv" in href for href in Links(response.text).hrefs
    )
