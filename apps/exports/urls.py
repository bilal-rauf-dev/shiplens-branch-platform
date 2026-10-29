from django.urls import path

from apps.exports.views import export_csv

urlpatterns = [
    path(f"exports/{code}.csv", export_csv, {"code": code}, name=f"export-{code}-csv")
    for code in ("collections", "unsent", "reports", "summary", "members", "audit")
]
