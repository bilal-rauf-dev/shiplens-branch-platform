from urllib.parse import parse_qs, urlsplit

import pytest
from django.urls import reverse

from apps.accounts.models import Role, User, UserBranchAssignment
from apps.accounts.permissions import PERMISSIONS
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.core.models import SystemSetting
from apps.core.routes import ROUTE_ACTIONS
from tests.rbac.registry import ROUTE_CASES


def test_t_rbac_registry_covers_every_protected_route():
    missing = ROUTE_ACTIONS.keys() - ROUTE_CASES.keys()
    obsolete = ROUTE_CASES.keys() - ROUTE_ACTIONS.keys()
    assert not missing, (
        f"Add request recipes to tests/rbac/registry.py: {sorted(missing)}"
    )
    assert not obsolete, f"Remove obsolete request recipes: {sorted(obsolete)}"


def domain_snapshot():
    """Permission denials may be audited, but must not change business records."""
    return {
        "branches": list(Branch.objects.order_by("pk").values()),
        "users": list(User.objects.order_by("pk").values()),
        "assignments": list(UserBranchAssignment.objects.order_by("pk").values()),
        "settings": list(SystemSetting.objects.order_by("pk").values()),
    }


@pytest.mark.parametrize("role", [*Role.values, "ANON"])
@pytest.mark.parametrize("url_name", ROUTE_ACTIONS)
def test_t_rbac_matrix_route(client, scenario, role, url_name):
    case = ROUTE_CASES.get(url_name)
    assert case is not None, f"Missing request recipe for {url_name}"
    fixture = case.fixture_factory(scenario)
    url = case.url_builder(url_name, fixture)
    if role != "ANON":
        client.force_login(
            scenario["actor"], backend="apps.accounts.backends.EmailBackend"
        )
    before = domain_snapshot()
    audit_count = AuditLog.objects.count()
    if case.method == "GET":
        response = client.get(url, data=fixture["data"])
    else:
        assert case.method == "POST", "Add explicit handling for a new HTTP method"
        response = client.post(url, data=fixture["data"])

    action = ROUTE_ACTIONS[url_name]
    allowed = role != "ANON" and role in PERMISSIONS[action]
    if allowed:
        assert response.status_code == case.expected_success_status
        if response.context and "form" in response.context:
            assert not response.context["form"].errors
        if case.method == "POST":
            assert AuditLog.objects.count() > audit_count, (
                "Successful mutation must be audited"
            )
    elif role == "ANON":
        assert response.status_code == 302
        destination = urlsplit(response.url)
        assert destination.path == reverse("account-login")
        assert parse_qs(destination.query) == {"next": [url]}
        assert domain_snapshot() == before
    else:
        assert response.status_code == 403
        assert domain_snapshot() == before
