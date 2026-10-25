"""Read-only account routing helpers."""

from apps.accounts.models import Role

ROLE_HOME_NAMES = {
    Role.SUPER_ADMIN: "dashboard-head-office",
    Role.FINANCE_REVIEWER: "dashboard-head-office",
    Role.CONTENT_EDITOR: "content-list",
    Role.BRANCH_LEAD: "dashboard-branch",
    Role.HR_LEAD: "application-list",
}


def role_home_name(user):
    """Return the placeholder destination for this user's single role."""
    return ROLE_HOME_NAMES[user.role]
