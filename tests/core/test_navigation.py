from html.parser import HTMLParser
from types import SimpleNamespace

import pytest
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.core.templatetags.navigation import nav_current


class CurrentLinks(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.links = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "a" and attributes.get("aria-current") == "page":
            self.links.append(attributes["href"])


@pytest.mark.parametrize(
    "route,target,expected",
    [
        ("branch-detail", "branch-list", True),
        ("city-edit", "branch-list", True),
        ("member-edit", "member-list", True),
        ("report-review-queue", "report-list", False),
        ("report-review-queue", "report-review-queue", True),
        ("volunteer-thanks", "volunteer-apply", True),
        ("home", "home", True),
        ("account-login", "home", False),
    ],
)
def test_nav_current_uses_resolved_sections(route, target, expected):
    request = SimpleNamespace(resolver_match=SimpleNamespace(url_name=route))
    assert nav_current({"request": request}, target) is expected


def test_nav_current_handles_error_pages_without_a_request():
    assert nav_current({}, "home") is False


@pytest.mark.django_db
@pytest.mark.parametrize("route", ["home", "volunteer-apply", "account-login"])
def test_public_header_marks_only_its_current_destination(client, route):
    response = client.get(reverse(route))
    assert response.status_code == 200
    assert CurrentLinks(response.text).links == [reverse(route)]


@pytest.mark.django_db
def test_staff_rail_and_mobile_menu_mark_the_detail_section(client, branch_factory):
    admin = User.objects.create_user(
        email="nav-admin@example.org",
        full_name="Navigation Admin",
        role=Role.SUPER_ADMIN,
    )
    branch = branch_factory()
    client.force_login(admin)
    response = client.get(reverse("branch-detail", kwargs={"pk": branch.pk}))
    assert response.status_code == 200
    assert CurrentLinks(response.text).links == [
        reverse("branch-list"),
        reverse("branch-list"),
    ]
