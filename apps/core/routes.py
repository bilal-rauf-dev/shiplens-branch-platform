"""Every reachable named route must be explicitly public or declare an action."""

ROUTE_ACTIONS = {
    "account-logout": "account.logout",
    "account-change-password": "account.change_password",
    "dashboard-head-office": "dashboard.head_office",
    "dashboard-branch": "dashboard.branch",
    "application-list": "application.list",
    "content-list": "content.list",
}

# Login handles signed-in visitors by redirecting them to their role's home.
PUBLIC_ROUTES = frozenset({"home", "account-login", "health"})
