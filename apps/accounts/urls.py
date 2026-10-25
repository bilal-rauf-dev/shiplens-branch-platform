from django.urls import path
from django.utils.translation import gettext_lazy as _

from apps.accounts.views import ChangePasswordView, LoginView, RoleHomeView, logout

urlpatterns = [
    path("accounts/login/", LoginView.as_view(), name="account-login"),
    path("accounts/logout/", logout, name="account-logout"),
    path(
        "accounts/change-password/",
        ChangePasswordView.as_view(),
        name="account-change-password",
    ),
    path(
        "app/dashboard/",
        RoleHomeView.as_view(
            required_action="dashboard.head_office",
            title=_("Dashboard"),
        ),
        name="dashboard-head-office",
    ),
    path(
        "app/my-branch/",
        RoleHomeView.as_view(required_action="dashboard.branch", title=_("My branch")),
        name="dashboard-branch",
    ),
    path(
        "app/applications/",
        RoleHomeView.as_view(
            required_action="application.list", title=_("Applications")
        ),
        name="application-list",
    ),
    path(
        "app/content/",
        RoleHomeView.as_view(required_action="content.list", title=_("Content")),
        name="content-list",
    ),
]
