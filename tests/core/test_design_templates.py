"""Check the shared MD3 shell, RTL, and the strict no-inline-style rule."""

import re
import runpy
from pathlib import Path

import pytest

from apps.accounts.models import Role, User

ROOT = Path(__file__).resolve().parents[2]
CHECKER = runpy.run_path(str(ROOT / "bin/check_conventions.py"))


@pytest.mark.django_db
@pytest.mark.parametrize("language", ["en", "ur"])
def test_design_stylesheets_are_loaded_in_order(client, language):
    response = client.get(f"/{language}/")
    assert response.status_code == 200
    order = [
        response.text.index(f"css/{name}.css")
        for name in ("tokens", "base", "components", "layout")
    ]
    assert order == sorted(order)
    assert ("css/urdu.css" in response.text) == (language == "ur")


def test_design_templates_have_no_inline_styles():
    for path in (ROOT / "templates").rglob("*.html"):
        assert not re.search(r"\bstyle\s*=", path.read_text(encoding="utf-8")), path


def test_design_css_uses_logical_properties():
    assert CHECKER["find_violations"](ROOT) == []


@pytest.mark.django_db
def test_design_urdu_public_and_staff_pages_are_rtl(client):
    for path in ("/ur/", "/ur/get-involved/"):
        response = client.get(path)
        assert response.status_code == 200
        assert 'lang="ur" dir="rtl"' in response.text
    admin = User.objects.create_user(
        email="rtl-design-admin@example.com",
        full_name="RTL admin",
        role=Role.SUPER_ADMIN,
    )
    client.force_login(admin)
    response = client.get("/ur/app/branches/")
    assert response.status_code == 200
    assert 'dir="rtl"' in response.text and 'class="staff-rail"' in response.text
    assert 'class="data-table"' in response.text
