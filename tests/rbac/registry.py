"""Explicit request recipes for every protected route; extend alongside new routes."""

from collections.abc import Callable
from dataclasses import dataclass

from django.urls import reverse

from apps.accounts.models import Role, User
from apps.accounts.services import assign_branch
from apps.branches.models import City
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
