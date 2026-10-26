from collections.abc import Callable
from dataclasses import dataclass

import pytest
from django.core.exceptions import PermissionDenied

from apps.accounts import services
from apps.accounts.models import Role
from apps.accounts.permissions import PERMISSIONS
from apps.branches import services as branch_services
from apps.branches.models import City
from tests.rbac.registry import (
    NEW_PASSWORD,
    assigned_user_object,
    assignment_payload,
    branch_object,
    create_branch_payload,
    create_city_payload,
    create_payload,
    edit_branch_payload,
    edit_city_payload,
    edit_payload,
    inactive_user_object,
    settings_payload,
    user_object,
)
from tests.rbac.test_matrix import domain_snapshot


@dataclass(frozen=True)
class ServiceCase:
    action: str
    invoke: Callable
    fixture_factory: Callable


def create_user(scenario, fixture):
    return services.create_user(scenario["actor"], **fixture["data"])


def update_user(scenario, fixture):
    return services.update_user(scenario["actor"], fixture["target"], **fixture["data"])


def deactivate_user(scenario, fixture):
    return services.set_user_active(scenario["actor"], fixture["target"], active=False)


def reactivate_user(scenario, fixture):
    return services.set_user_active(scenario["actor"], fixture["target"], active=True)


def reset_password(scenario, fixture):
    return services.reset_temporary_password(scenario["actor"], fixture["target"])


def assign_branch(scenario, fixture):
    return services.assign_branch(
        scenario["actor"], fixture["target"], fixture["branch"]
    )


def remove_assignment(scenario, fixture):
    return services.remove_branch_assignment(
        scenario["actor"], fixture["target"], fixture["branch"].pk
    )


def update_settings(scenario, fixture):
    return services.update_settings(scenario["actor"], **fixture["data"])


def create_branch(scenario, fixture):
    data = fixture["data"].copy()
    data["city"] = City.objects.get(pk=data["city"])
    return branch_services.create_branch(scenario["actor"], **data)


def update_branch(scenario, fixture):
    return branch_services.update_branch(
        scenario["actor"], fixture["branch"], **fixture["data"]
    )


def transition_branch(scenario, fixture):
    return branch_services.transition(scenario["actor"], fixture["branch"], "activate")


def create_city(scenario, fixture):
    return branch_services.create_city(scenario["actor"], **fixture["data"])


def update_city(scenario, fixture):
    return branch_services.update_city(
        scenario["actor"], fixture["city"], **fixture["data"]
    )


SERVICE_CASES = {
    "create_branch": ServiceCase("branch.create", create_branch, create_branch_payload),
    "update_branch": ServiceCase("branch.update", update_branch, edit_branch_payload),
    "transition_branch": ServiceCase(
        "branch.transition", transition_branch, branch_object
    ),
    "create_city": ServiceCase("city.manage", create_city, create_city_payload),
    "update_city": ServiceCase("city.manage", update_city, edit_city_payload),
    "create_user": ServiceCase("user.create", create_user, create_payload),
    "update_user": ServiceCase("user.update", update_user, edit_payload),
    "deactivate_user": ServiceCase("user.update", deactivate_user, user_object),
    "reactivate_user": ServiceCase(
        "user.update", reactivate_user, inactive_user_object
    ),
    "reset_password": ServiceCase("user.reset_password", reset_password, user_object),
    "assign_branch": ServiceCase(
        "assignment.manage", assign_branch, assignment_payload
    ),
    "remove_assignment": ServiceCase(
        "assignment.manage", remove_assignment, assigned_user_object
    ),
    "update_settings": ServiceCase(
        "settings.update", update_settings, settings_payload
    ),
}

DENIED_CASES = [
    pytest.param(name, role, id=f"{name}-{role}")
    for name, case in SERVICE_CASES.items()
    for role in [*Role.values, "ANON"]
    if role == "ANON" or role not in PERMISSIONS[case.action]
]


@pytest.mark.parametrize("service_name,role", DENIED_CASES)
def test_t_rbac_service_wrong_role(scenario, service_name, role):
    case = SERVICE_CASES[service_name]
    fixture = case.fixture_factory(scenario)
    before = domain_snapshot()
    with pytest.raises(PermissionDenied):
        case.invoke(scenario, fixture)
    assert domain_snapshot() == before


@pytest.mark.parametrize("role", ["ANON"])
def test_t_rbac_service_password_change_requires_identity(scenario, rf, role):
    request = rf.post("/en/accounts/change-password/")
    request.user = scenario["actor"]
    before = domain_snapshot()
    with pytest.raises(PermissionDenied):
        services.change_password(request, "unused", NEW_PASSWORD)
    assert domain_snapshot() == before
