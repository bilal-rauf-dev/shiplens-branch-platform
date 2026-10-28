from django.urls import path

from apps.finance import report_views as views

urlpatterns = [
    path("app/reports/", views.ReportListView.as_view(), name="report-list"),
    path(
        "app/reports/review/",
        views.ReportReviewQueueView.as_view(),
        name="report-review-queue",
    ),
    path(
        "app/reports/<int:pk>/", views.ReportDetailView.as_view(), name="report-detail"
    ),
    path("app/reports/<int:pk>/narrative/", views.save, name="report-save"),
    path("app/reports/<int:pk>/submit/", views.submit, name="report-submit"),
    path("app/reports/<int:pk>/resubmit/", views.resubmit, name="report-resubmit"),
    path("app/reports/<int:pk>/return/", views.return_report, name="report-return"),
    path("app/reports/<int:pk>/approve/", views.approve, name="report-approve"),
]
