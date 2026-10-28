from django.urls import path
from django.utils.translation import gettext_lazy as _

from apps.accounts import views
from apps.accounts.views import ChangePasswordView, LoginView, RoleHomeView, logout

urlpatterns = [
    path("app/users/", views.UserListView.as_view(), name="user-list"),
    path("app/users/create/", views.UserCreateView.as_view(), name="user-create"),
    path("app/users/<int:pk>/", views.UserDetailView.as_view(), name="user-detail"),
    path("app/users/<int:pk>/edit/", views.UserEditView.as_view(), name="user-edit"),
    path(
        "app/users/<int:pk>/deactivate/", views.deactivate_user, name="user-deactivate"
    ),
    path(
        "app/users/<int:pk>/reactivate/", views.reactivate_user, name="user-reactivate"
    ),
    path(
        "app/users/<int:pk>/reset-password/",
        views.reset_user_password,
        name="user-reset-password",
    ),
    path(
        "app/users/<int:pk>/assignments/",
        views.assign_user_branch,
        name="user-assign-branch",
    ),
    path(
        "app/users/<int:pk>/assignments/<int:branch_id>/remove/",
        views.remove_user_branch,
        name="user-remove-branch",
    ),
    path("app/settings/", views.SettingsView.as_view(), name="settings-view"),
    path(
        "app/settings/update/",
        views.SettingsUpdateView.as_view(),
        name="settings-update",
    ),
    path("accounts/login/", LoginView.as_view(), name="account-login"),
    path("accounts/logout/", logout, name="account-logout"),
    path(
        "accounts/change-password/",
        ChangePasswordView.as_view(),
        name="account-change-password",
    ),
    path(
        "app/content/",
        RoleHomeView.as_view(required_action="content.list", title=_("Content")),
        name="content-list",
    ),
]
