"""Every reachable named route must be explicitly public or declare an action."""

ROUTE_ACTIONS = {
    "application-detail": "application.view",
    "application-accept": "application.accept",
    "application-decline": "application.decline",
    "application-reassign": "application.reassign_branch",
    "member-detail": "member.view",
    "branch-list": "branch.list",
    "branch-detail": "branch.view",
    "branch-create": "branch.create",
    "branch-edit": "branch.update",
    "city-list": "city.manage",
    "city-create": "city.manage",
    "city-edit": "city.manage",
    "branch-transition": "branch.transition",
    "user-list": "user.list",
    "user-create": "user.create",
    "user-detail": "user.view",
    "user-edit": "user.update",
    "user-deactivate": "user.update",
    "user-reactivate": "user.update",
    "user-reset-password": "user.reset_password",
    "user-assign-branch": "assignment.manage",
    "user-remove-branch": "assignment.manage",
    "settings-view": "settings.view",
    "settings-update": "settings.update",
    "account-logout": "account.logout",
    "account-change-password": "account.change_password",
    "dashboard-head-office": "dashboard.head_office",
    "dashboard-branch": "dashboard.branch",
    "application-list": "application.list",
    "content-list": "content.list",
}

# Login handles signed-in visitors by redirecting them to their role's home.
PUBLIC_ROUTES = frozenset(
    {"home", "account-login", "health", "volunteer-apply", "volunteer-thanks"}
)
