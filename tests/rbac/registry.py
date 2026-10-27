"""Explicit request recipes for every protected route; extend alongside new routes."""

from collections.abc import Callable
from dataclasses import dataclass

from django.urls import reverse

from apps.accounts.models import Role, User
from apps.accounts.services import assign_branch
from apps.branches.models import Branch, City
from apps.volunteers import services as volunteer_services
from apps.volunteers.forms import ApplicationForm
from apps.volunteers.models import Team, VolunteerRole
from tests.accounts.conftest import TEST_PASSWORD

NEW_PASSWORD = "Spruce!Harbor-92-Lantern"  # noqa: S105 -- test-only credential.


@dataclass(frozen=True)
class RouteCase:
    method: str
    url_builder: Callable
    fixture_factory: Callable
    expected_success_status: int


def page_url(name, fixture):
    return reverse(name)


def transition_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["branch"].pk, "action": "activate"})


def branch_object(scenario):
    return {"branch": scenario["branch"], "data": {}}


def team_object(scenario):
    team = Team.objects.create(branch=scenario["branch"], name="Teaching")
    return {"team": team, "data": {"name": "Community outreach"}}


def team_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["team"].pk})


def team_create_url(name, fixture):
    return reverse(name, kwargs={"branch_pk": fixture["branch"].pk})


def team_create_payload(scenario):
    return {"branch": scenario["branch"], "data": {"name": "Teaching"}}


def volunteer_role_payload(scenario):
    return {
        "volunteer_role": VolunteerRole.objects.get(code="VOLUNTEER"),
        "data": {"name_en": "Mentor", "name_ur": "رہنما", "sort_order": 4},
    }


def volunteer_role_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["volunteer_role"].pk})


def application_object(scenario):
    """Use a valid Pending applicant in the actor's assigned branch."""
    form = ApplicationForm(
        {
            "full_name": "Matrix Applicant",
            "email": "matrix-applicant@example.com",
            "phone": "03001234567",
            "date_of_birth": "2000-01-01",
            "preferred_branch": scenario["branch"].pk,
            "interests": ["education"],
            "availability": ["weekends"],
            "motivation": "I would like to volunteer in my local community.",
            "preferred_language": "en",
            "privacy_consent": True,
        }
    )
    assert form.is_valid(), form.errors
    application = volunteer_services.submit_application(form.cleaned_data, None)
    target = Branch.objects.create(
        code="BR-LHE-01",
        city=City.objects.get(code="LHE"),
        name_en="Other branch",
        name_ur="دوسری شاخ",
    )
    return {
        "application": application,
        "target_branch": target,
        "volunteer_role": VolunteerRole.objects.get(code="VOLUNTEER"),
        "data": {},
    }


def application_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["application"].pk})


def accept_payload(scenario):
    fixture = application_object(scenario)
    fixture["data"] = {"role_id": fixture["volunteer_role"].pk}
    return fixture


def decline_payload(scenario):
    fixture = application_object(scenario)
    fixture["data"] = {"reason": "No capacity at present"}
    return fixture


def reassign_payload(scenario):
    fixture = application_object(scenario)
    fixture["data"] = {"branch_id": fixture["target_branch"].pk}
    return fixture


def member_object(scenario):
    fixture = application_object(scenario)
    reviewer = User.objects.create_user(
        email="matrix-reviewer@example.com",
        full_name="Matrix Reviewer",
        role=Role.HR_LEAD,
    )
    assign_branch(scenario["admin"], reviewer, scenario["branch"])
    fixture["member"] = volunteer_services.accept_application(
        reviewer, fixture["application"].pk, role_id=fixture["volunteer_role"].pk
    )
    return fixture


def member_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["member"].pk})


def branch_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["branch"].pk})


def city_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["city"].pk})


def city_object(scenario):
    return {"city": scenario["branch"].city, "data": {}}


def create_city_payload(scenario):
    return {"data": {"code": "ZZZ", "name_en": "New City", "name_ur": "نیا شہر"}}


def edit_city_payload(scenario):
    return {
        "city": scenario["branch"].city,
        "data": {"name_en": "Edited City", "name_ur": "تبدیل شدہ شہر"},
    }


def create_branch_payload(scenario):
    return {
        "data": {
            "city": City.objects.get(code="ISB").pk,
            "name_en": "New Branch",
            "name_ur": "نئی شاخ",
            "address_en": "",
            "address_ur": "",
            "phone": "",
            "email": "",
        }
    }


def edit_branch_payload(scenario):
    return {
        "branch": scenario["branch"],
        "data": {
            "name_en": "Edited Branch",
            "name_ur": "تبدیل شدہ شاخ",
            "address_en": "",
            "address_ur": "",
            "phone": "",
            "email": "",
        },
    }


def user_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["target"].pk})


def assignment_url(name, fixture):
    return reverse(
        name,
        kwargs={
            "pk": fixture["target"].pk,
            "branch_id": fixture["branch"].pk,
        },
    )


def no_object(scenario):
    return {"data": {}}


def user_object(scenario):
    # User administration has GLOBAL scope. Never target the only active admin.
    target = User.objects.create_user(
        email="rbac-target@example.com",
        full_name="Target Operator",
        role=Role.BRANCH_LEAD,
    )
    return {"target": target, "data": {}}


def inactive_user_object(scenario):
    target = User.objects.create_user(
        email="rbac-target@example.com",
        full_name="Inactive Operator",
        role=Role.BRANCH_LEAD,
        is_active=False,
    )
    return {"target": target, "data": {}}


def create_payload(scenario):
    return {
        "data": {
            "email": "rbac-created@example.com",
            "full_name": "Created Operator",
            "role": Role.HR_LEAD,
        }
    }


def edit_payload(scenario):
    fixture = user_object(scenario)
    fixture["data"] = {"full_name": "Edited Operator", "role": Role.HR_LEAD}
    return fixture


def assignment_payload(scenario):
    fixture = user_object(scenario)
    fixture["data"] = {"branch_id": scenario["branch"].pk}
    fixture["branch"] = scenario["branch"]
    return fixture


def assigned_user_object(scenario):
    fixture = assignment_payload(scenario)
    assign_branch(scenario["admin"], fixture["target"], fixture["branch"])
    return fixture


def password_payload(scenario):
    return {
        "data": {
            "old_password": TEST_PASSWORD,
            "new_password1": NEW_PASSWORD,
            "new_password2": NEW_PASSWORD,
        }
    }


def settings_payload(scenario):
    return {
        "data": {
            "collection_lock_days": 3,
            "allow_submit_current_week": True,
            "min_volunteer_age": 17,
            "apply_rate_per_hour": 6,
        }
    }


# The four columns are method, URL builder, in-scope fixture factory and success
# status. Payloads must be valid so a validation error cannot masquerade as denial.
ROUTE_CASES = {
    "team-list": RouteCase("GET", page_url, no_object, 200),
    "team-create": RouteCase("POST", team_create_url, team_create_payload, 302),
    "team-edit": RouteCase("POST", team_url, team_object, 302),
    "team-deactivate": RouteCase("POST", team_url, team_object, 302),
    "volunteer-role-list": RouteCase("GET", page_url, no_object, 200),
    "volunteer-role-create": RouteCase("POST", page_url, volunteer_role_payload, 302),
    "volunteer-role-edit": RouteCase(
        "POST", volunteer_role_url, volunteer_role_payload, 302
    ),
    "volunteer-role-deactivate": RouteCase(
        "POST", volunteer_role_url, volunteer_role_payload, 302
    ),
    "application-detail": RouteCase("GET", application_url, application_object, 200),
    "application-accept": RouteCase("POST", application_url, accept_payload, 302),
    "application-decline": RouteCase("POST", application_url, decline_payload, 302),
    "application-reassign": RouteCase("POST", application_url, reassign_payload, 302),
    "member-detail": RouteCase("GET", member_url, member_object, 200),
    "branch-transition": RouteCase("POST", transition_url, branch_object, 302),
    "branch-list": RouteCase("GET", page_url, no_object, 200),
    "branch-detail": RouteCase("GET", branch_url, branch_object, 200),
    "branch-create": RouteCase("POST", page_url, create_branch_payload, 302),
    "branch-edit": RouteCase("POST", branch_url, edit_branch_payload, 302),
    "city-list": RouteCase("GET", page_url, no_object, 200),
    "city-create": RouteCase("POST", page_url, create_city_payload, 302),
    "city-edit": RouteCase("POST", city_url, edit_city_payload, 302),
    "user-list": RouteCase("GET", page_url, no_object, 200),
    "user-create": RouteCase("POST", page_url, create_payload, 200),
    "user-detail": RouteCase("GET", user_url, user_object, 200),
    "user-edit": RouteCase("POST", user_url, edit_payload, 302),
    "user-deactivate": RouteCase("POST", user_url, user_object, 302),
    "user-reactivate": RouteCase("POST", user_url, inactive_user_object, 302),
    "user-reset-password": RouteCase("POST", user_url, user_object, 200),
    "user-assign-branch": RouteCase("POST", user_url, assignment_payload, 302),
    "user-remove-branch": RouteCase("POST", assignment_url, assigned_user_object, 302),
    "settings-view": RouteCase("GET", page_url, no_object, 200),
    "settings-update": RouteCase("POST", page_url, settings_payload, 302),
    "account-logout": RouteCase("POST", page_url, no_object, 302),
    "account-change-password": RouteCase("POST", page_url, password_payload, 302),
    "dashboard-head-office": RouteCase("GET", page_url, no_object, 200),
    "dashboard-branch": RouteCase("GET", page_url, no_object, 200),
    "application-list": RouteCase("GET", page_url, no_object, 200),
    "content-list": RouteCase("GET", page_url, no_object, 200),
}
