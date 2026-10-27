"""Read-only account routing helpers."""

from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session

from apps.accounts.models import Role, User
from apps.branches.models import Branch, BranchStatus
from apps.core import clock

ROLE_HOME_NAMES = {
    Role.SUPER_ADMIN: "dashboard-head-office",
    Role.FINANCE_REVIEWER: "dashboard-head-office",
    Role.CONTENT_EDITOR: "content-list",
    Role.BRANCH_LEAD: "dashboard-branch",
    Role.HR_LEAD: "application-list",
}


def role_home_name(user):
    """Return the landing page for this user's single role."""
    return ROLE_HOME_NAMES[user.role]


def users():
    return User.objects.order_by("email")


def assignable_branches():
    return Branch.objects.exclude(status=BranchStatus.CLOSED).order_by("code")


def user_session_keys(user):
    """Find server-side sessions belonging to the account being revoked."""
    return [
        session.session_key
        for session in Session.objects.filter(expire_date__gt=clock.now()).iterator()
        if session.get_decoded().get(SESSION_KEY) == str(user.pk)
    ]
