import io
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext
from pypdf import PdfReader

from apps.accounts.models import Role
from apps.audit.models import AuditLog
from apps.finance.models import WeeklyReport
from tests.exports.test_csv import sign_in

pytestmark = pytest.mark.django_db


def report(week="2026-10-05"):
    return WeeklyReport.objects.get(branch__code="BR-KHI-01", week_start=week)


def text(response):
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    return "\n".join(
        page.extract_text() for page in PdfReader(io.BytesIO(response.content)).pages
    )


def test_t_exp_pdf_report(client, sample_data):
    sign_in(client, Role.SUPER_ADMIN)
    item = report()
    response = client.get(reverse("export-report-pdf", args=[item.pk]))
    extracted = text(response)
    assert "BR-KHI-01" in extracted
    assert "25,250.50" in extracted
    assert "Locked" in extracted
    assert item.snapshot_hash in extracted.replace("\n", "")
    assert "DRAFT — NOT APPROVED" not in extracted
    assert "Report approved" in extracted
    event = AuditLog.objects.filter(action="export.pdf").latest("pk")
    assert event.metadata == {
        "export_code": "X4",
        "filters": {"report": item.pk},
        "row_count": 2,
        "lang": "en",
    }


def test_t_exp_pdf_watermark(client, sample_data):
    sign_in(client, Role.BRANCH_LEAD)
    extracted = text(
        client.get(reverse("export-report-pdf", args=[report("2026-10-19").pk]))
    )
    assert "DRAFT" in extracted
    assert "NOT APPROVED" in extracted


def test_t_exp_pdf_ur(client, sample_data):
    sign_in(client, Role.SUPER_ADMIN)
    from apps.exports.pdf import render_pdf

    with patch("apps.exports.pdf_views.render_pdf", wraps=render_pdf) as renderer:
        response = client.get(
            reverse("export-report-pdf", args=[report().pk]), {"lang": "ur"}
        )
    extracted = text(response)
    with translation.override("ur"):
        assert gettext("Issues") in extracted
    context = renderer.call_args.args[1]
    assert context["lang"] == "ur"
    from django.template.loader import render_to_string

    markup = render_to_string("pdf/weekly_report.html", context)
    assert 'lang="ur" dir="rtl"' in markup
    assert "<bdi>BR-KHI-01</bdi>" in markup
    fonts = []
    for page in PdfReader(io.BytesIO(response.content)).pages:
        for resource in page["/Resources"]["/Font"].values():
            font = resource.get_object()
            fonts.append(str(font.get("/BaseFont", "")))
            if "Naskh" in fonts[-1]:
                descriptor = font["/DescendantFonts"][0].get_object()["/FontDescriptor"]
                assert any(
                    key in descriptor
                    for key in ["/FontFile", "/FontFile2", "/FontFile3"]
                )
    assert any("Naskh" in name for name in fonts)


def test_summary_pdf_smoke(client, sample_data, settings):
    sign_in(client, Role.FINANCE_REVIEWER)
    settings.DEMO_MODE = True
    extracted = text(client.get(reverse("export-summary-pdf"), {"period": "2026-10"}))
    assert "73,250.50" in extracted
    assert "43,250.50" in extracted
    assert "35,250.50" in extracted
    assert "BR-KHI-01" in extracted and "BR-LHE-01" in extracted
    assert "Demo data" in extracted
    assert "page 1 /" in extracted


def test_summary_pdf_row_cap(client, sample_data, settings):
    sign_in(client, Role.SUPER_ADMIN)
    settings.BUSINESS_RULES = {**settings.BUSINESS_RULES, "export_summary_max_rows": 1}
    with patch("apps.exports.pdf_views.render_pdf") as renderer:
        response = client.get(reverse("export-summary-pdf"), {"period": "2026-10"})
    assert response.status_code == 400
    assert "CSV" in response.text
    assert reverse("export-summary-csv") in response.text
    renderer.assert_not_called()
    assert not AuditLog.objects.filter(action="export.pdf").exists()


def test_pdf_invalid_period(client, sample_data):
    sign_in(client, Role.SUPER_ADMIN)
    assert (
        client.get(reverse("export-summary-pdf"), {"period": "invalid"}).status_code
        == 400
    )


def test_pdf_and_csv_share_rate_limit(client, sample_data, settings):
    sign_in(client, Role.SUPER_ADMIN)
    settings.BUSINESS_RULES = {**settings.BUSINESS_RULES, "export_rate_per_hour": 1}
    text(client.get(reverse("export-report-pdf", args=[report().pk])))
    assert client.get(reverse("export-summary-pdf")).status_code == 429
    assert client.get(reverse("export-collections-csv")).status_code == 429


def test_pdf_render_failure_does_not_record_delivery(client, sample_data):
    sign_in(client, Role.SUPER_ADMIN)
    with patch(
        "apps.exports.pdf_views.render_pdf", side_effect=RuntimeError("render failed")
    ):
        with pytest.raises(RuntimeError):
            client.get(reverse("export-report-pdf", args=[report().pk]))
    assert not AuditLog.objects.filter(action="export.pdf").exists()
