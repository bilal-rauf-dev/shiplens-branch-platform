"""The night-city presentation keeps public content and staff scripts separate."""

import re
from html.parser import HTMLParser

import pytest
from django.utils import formats, translation
from django.utils.translation import gettext

from apps.accounts.models import User
from tests.publicsite.test_pages import PATHS

pytestmark = pytest.mark.django_db


class Elements(HTMLParser):
    """Expose tag attributes without depending on template whitespace."""

    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


@pytest.mark.parametrize("language", ["en", "ur"])
def test_t_pub_night_city_home(client, sample_data, language):
    response = client.get(f"/{language}/")
    assert response.status_code == 200
    source = response.text
    elements = Elements(source).tags
    skylines = [attrs for tag, attrs in elements if tag == "svg"]
    assert len(skylines) == 2
    assert all(attrs["class"] == "skyline" for attrs in skylines)
    assert all(attrs["aria-hidden"] == "true" for attrs in skylines)
    for number in (4, 3, 1):
        assert f"<strong>{number}</strong>" in source
    nav = re.search(r'<nav class="public-navigation"[^>]*>(.*?)</nav>', source, re.S)
    links = [attrs["href"] for tag, attrs in Elements(nav[1]).tags if tag == "a"]
    assert links == [
        f"/{language}/{path}/" for path in ("about", "programs", "branches", "events")
    ]
    brand = next(attrs for tag, attrs in elements if attrs.get("class") == "brand")
    assert brand["href"] == f"/{language}/" and brand["aria-current"] == "page"
    with translation.override(language):
        assert f'<span class="visually-hidden">{gettext("Log in")}</span>' in source
        assert f">{gettext('Get involved')}</a>" in source
        featured = response.context["featured"]["event_start"]
        assert f'class="ticket-stub__day">{featured:%d}</bdi>' in source
        month = formats.date_format(featured, "M Y")
        assert f'class="ticket-stub__month">{month}</span>' in source


@pytest.mark.parametrize("language", ["en", "ur"])
@pytest.mark.parametrize("path", PATHS)
def test_t_pub_redesign_has_no_scripts(client, sample_data, language, path):
    response = client.get(f"/{language}/{path}")
    assert response.status_code == 200
    assert "<script" not in response.text
    assert "js/busy.js" not in response.text
    assert "css/public.css" in response.text


@pytest.mark.parametrize("language", ["en", "ur"])
def test_t_pub_login_loader(client, language):
    response = client.get(f"/{language}/accounts/login/")
    assert response.status_code == 200
    assert response.text.count("js/busy.js") == 1


@pytest.mark.parametrize("language", ["en", "ur"])
def test_t_pub_staff_loader_boundary(client, sample_data, language):
    client.force_login(User.objects.get(role="FINANCE_REVIEWER"))
    response = client.get(f"/{language}/app/dashboard/?period=2026-10")
    assert response.status_code == 200
    assert response.text.count("js/busy.js") == 1
    assert "css/public.css" not in response.text
    assert response.text.count('class="spinner"') == 2
    # Signing in must not add staff scripts to a public content page.
    assert "<script" not in client.get(f"/{language}/").text
