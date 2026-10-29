from django.urls import path

from apps.exports import pdf_views
from apps.exports.views import export_csv

urlpatterns = [
    path(f"exports/{code}.csv", export_csv, {"code": code}, name=f"export-{code}-csv")
    for code in ("collections", "unsent", "reports", "summary", "members", "audit")
]
urlpatterns += [
    path(
        "exports/reports/<int:pk>.pdf",
        pdf_views.weekly_report,
        name="export-report-pdf",
    ),
    path("exports/summary.pdf", pdf_views.monthly_summary, name="export-summary-pdf"),
]
