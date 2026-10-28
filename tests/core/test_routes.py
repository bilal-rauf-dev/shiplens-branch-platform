from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import polib
import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import Client
from django.urls import URLPattern, get_resolver, reverse
from django.views.generic import TemplateView

from apps.accounts.models import Role, User
from apps.accounts.permissions import PERMISSIONS
from apps.accounts.services import assign_branch
from apps.core.middleware import RouteRegistryMiddleware
from apps.core.routes import PUBLIC_ROUTES, ROUTE_ACTIONS
from apps.core.views import PermissionRequiredMixin, server_error


def named_routes(resolver, namespaces=()):
    """Walk included URLconfs using the same qualified names as the middleware."""
    names = []
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLPattern):
            if pattern.name:
                names.append(":".join((*namespaces, pattern.name)))
        else:
            child_namespaces = namespaces
            if pattern.namespace:
                child_namespaces = (*namespaces, pattern.namespace)
            names.extend(named_routes(pattern, child_namespaces))
    return names


def test_t_rbac_routes():
    names = named_routes(get_resolver())
    assert len(names) == len(set(names)), "Route names must be unique"
    assert set(names) == ROUTE_ACTIONS.keys() | PUBLIC_ROUTES
    assert ROUTE_ACTIONS.keys().isdisjoint(PUBLIC_ROUTES)
    assert set(ROUTE_ACTIONS.values()) <= PERMISSIONS.keys()


@pytest.fixture
def staff(db):
    return User.objects.create_user(
        email="registry@example.com",
        full_name="Registry Operator",
        role=Role.SUPER_ADMIN,
    )


@pytest.fixture
def staff_client(client, staff, clock):
    client.force_login(staff, backend="apps.accounts.backends.EmailBackend")
    return client


@pytest.fixture
def test_routes(settings, monkeypatch):
    settings.ROOT_URLCONF = "tests.core.route_urls"
    for name, action in {
        "registry-branch": "branch.view",
        "registry-denied": "dashboard.head_office",
        "registry-crash": "dashboard.head_office",
    }.items():
        monkeypatch.setitem(ROUTE_ACTIONS, name, action)


@pytest.mark.parametrize("path", ["unregistered", "unnamed", "namespaced"])
def test_unregistered_route_is_404_for_every_visitor(
    client, staff_client, test_routes, path
):
    for visitor in (Client(), staff_client):
        response = visitor.get(f"/en/registry/{path}/")
        assert response.status_code == 404
        assert "An unregistered view must never run" not in response.text


def test_force_change_cannot_bypass_registration(staff, staff_client, test_routes):
    User.objects.filter(pk=staff.pk).update(must_change_password=True)
    assert staff_client.get("/en/registry/unregistered/").status_code == 404
    assert staff_client.get("/en/app/dashboard/").url == "/en/accounts/change-password/"


@pytest.mark.parametrize("language", ["en", "ur"])
def test_private_route_redirects_to_localized_login(client, language):
    destination = f"/{language}/app/content/?search=two%20words&page=2"
    response = client.get(destination)
    assert response.status_code == 302
    parsed = urlsplit(response.url)
    assert parsed.path == f"/{language}/accounts/login/"
    assert parse_qs(parsed.query) == {"next": [destination]}


def test_registered_route_denies_wrong_role(staff_client):
    assert staff_client.get("/en/app/my-branch/").status_code == 403
    assert staff_client.get("/en/app/dashboard/").status_code == 200


@pytest.mark.parametrize("language", ["en", "ur"])
def test_public_routes_remain_public(client, language):
    assert client.get(f"/{language}/").status_code == 200
    assert client.get(f"/{language}/accounts/login/").status_code == 200


@pytest.mark.parametrize("path", ["/health", "/static/css/tokens.css"])
def test_registry_exemptions(rf, path):
    # Exemptions must work even when no resolver/auth state is available.
    middleware = RouteRegistryMiddleware(lambda request: None)
    assert middleware.process_view(rf.get(path), None, (), {}) is None


def test_static_exemption_does_not_match_similar_prefix(rf):
    request = rf.get("/static-private/")
    request.resolver_match = SimpleNamespace(view_name="unknown")
    with pytest.raises(Http404):
        RouteRegistryMiddleware(lambda request: None).process_view(
            request, None, (), {}
        )


def test_t_rbac_scope_detail_view(staff, staff_client, test_routes, branch_factory):
    assigned = branch_factory()
    other = branch_factory(code="BR-LHE-01", name_en="Lahore")
    lead = User.objects.create_user(
        email="scoped@example.com", full_name="Scoped Lead", role=Role.BRANCH_LEAD
    )
    assign_branch(staff, lead, assigned)
    staff_client.force_login(lead, backend="apps.accounts.backends.EmailBackend")
    allowed = staff_client.get(reverse("registry-branch", args=[assigned.pk]))
    hidden = staff_client.get(reverse("registry-branch", args=[other.pk]))
    missing = staff_client.get(reverse("registry-branch", args=[other.pk + 100]))
    assert allowed.status_code == 200
    assert allowed.text == assigned.code
    assert hidden.status_code == missing.status_code == 404
    assert hidden.content == missing.content
    assert other.code not in hidden.text


class ProtectedView(PermissionRequiredMixin, TemplateView):
    required_action = "dashboard.branch"
    template_name = "accounts/role_home.html"


def test_mixin_rechecks_permission_without_middleware(rf, staff):
    request = rf.get("/en/app/my-branch/")
    request.user = staff
    with pytest.raises(PermissionDenied):
        ProtectedView.as_view()(request)
    with pytest.raises(PermissionDenied):
        ProtectedView.as_view(required_action=None)(request)
    request.user = AnonymousUser()
    assert ProtectedView.as_view()(request).status_code == 302
    staff.role = Role.BRANCH_LEAD
    request.user = staff
    assert ProtectedView.as_view()(request).status_code == 200


@pytest.fixture
def error_catalog(settings, tmp_path):
    source = settings.BASE_DIR / "locale" / "ur" / "LC_MESSAGES" / "django.po"
    compiled = tmp_path / "ur" / "LC_MESSAGES" / "django.mo"
    compiled.parent.mkdir(parents=True)
    polib.pofile(str(source)).save_as_mofile(str(compiled))
    settings.LOCALE_PATHS = [tmp_path]


@pytest.mark.parametrize(
    "path,status,title,urdu_title",
    [
        ("registry/denied/", 403, "Access denied", "رسائی کی اجازت نہیں"),
        ("missing-private-record/", 404, "Page not found", "صفحہ نہیں ملا"),
        ("registry/crash/", 500, "Something went wrong", "کچھ غلط ہو گیا"),
    ],
)
@pytest.mark.parametrize("language,direction", [("en", "ltr"), ("ur", "rtl")])
def test_t_sec_errors_are_generic_and_localized(
    staff_client,
    test_routes,
    error_catalog,
    path,
    status,
    title,
    urdu_title,
    language,
    direction,
):
    staff_client.raise_request_exception = False
    response = staff_client.get(f"/{language}/{path}")
    assert response.status_code == status
    assert (title if language == "en" else urdu_title) in response.text
    assert f'<html lang="{language}" dir="{direction}">' in response.text
    for private_text in (
        "private entity details",
        "private database details",
        "Traceback",
        "missing-private-record",
        "RuntimeError",
        "PermissionDenied",
    ):
        assert private_text not in response.text


@pytest.mark.django_db
def test_server_error_rendering_needs_no_database(rf, django_assert_num_queries):
    with django_assert_num_queries(0):
        response = server_error(rf.get("/en/"))
    assert response.status_code == 500
