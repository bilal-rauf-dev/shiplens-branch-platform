from django.urls import path
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Role
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
            allowed_roles=(Role.SUPER_ADMIN, Role.FINANCE_REVIEWER),
            title=_("Dashboard"),
        ),
        name="dashboard-head-office",
    ),
    path(
        "app/my-branch/",
        RoleHomeView.as_view(allowed_roles=(Role.BRANCH_LEAD,), title=_("My branch")),
        name="dashboard-branch",
    ),
    path(
        "app/applications/",
        RoleHomeView.as_view(
            allowed_roles=(Role.SUPER_ADMIN, Role.HR_LEAD), title=_("Applications")
        ),
        name="application-list",
    ),
    path(
        "app/content/",
        RoleHomeView.as_view(
            allowed_roles=(Role.SUPER_ADMIN, Role.CONTENT_EDITOR), title=_("Content")
        ),
        name="content-list",
    ),
]
