from django.urls import path

from apps.dashboard.views import BranchDashboardView, DashboardView, HRDashboardView

urlpatterns = [
    path("app/dashboard/", DashboardView.as_view(), name="dashboard-head-office"),
    path("app/my-branch/", BranchDashboardView.as_view(), name="dashboard-branch"),
    path("app/hr/", HRDashboardView.as_view(), name="dashboard-hr"),
]
