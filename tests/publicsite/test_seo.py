from html.parser import HTMLParser
from xml.etree import ElementTree

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.cms import services
from apps.cms.models import ContentItem
from tests.publicsite.test_pages import PATHS

pytestmark = pytest.mark.django_db


class Metadata(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.links = []
        self.meta = {}
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "link":
            self.links.append(attributes)
        if tag == "meta":
            self.meta[attributes.get("name") or attributes.get("property")] = (
                attributes.get("content")
            )


@pytest.mark.parametrize("language", ["en", "ur"])
@pytest.mark.parametrize("path", PATHS)
def test_t_pub_seo(client, sample_data, language, path):
    url = f"/{language}/{path}"
    response = client.get(url)
    metadata = Metadata(response.text)
    assert metadata.meta["description"]
    assert metadata.meta["og:description"] == metadata.meta["description"]
    assert metadata.meta["og:title"]
    assert metadata.meta["og:image"].startswith("http://testserver/static/")
    assert {
        link["href"] for link in metadata.links if link.get("rel") == "canonical"
    } == {f"http://testserver{url}"}
    alternates = {
        link["hreflang"]: link["href"]
        for link in metadata.links
        if link.get("rel") == "alternate"
    }
    assert alternates == {
        "en": f"http://testserver/en/{path}",
        "ur": f"http://testserver/ur/{path}",
        "x-default": f"http://testserver/en/{path}",
    }


def test_metadata_stays_on_published_snapshot(client, sample_data):
    item = ContentItem.objects.get(slug="education-support")
    editor = User.objects.get(role="CONTENT_EDITOR")
    values = {
        row.locale: {
            "title": row.title,
            "summary": "UNPUBLISHED DESCRIPTION",
            "body_md": row.body_md,
        }
        for row in item.translations.all()
    }
    services.update(editor, item.pk, translations=values)
    response = client.get("/en/programs/education-support/")
    assert "UNPUBLISHED DESCRIPTION" not in response.text


def test_sitemap_has_localized_public_urls_and_no_private_or_draft_urls(
    client, sample_data
):
    response = client.get(reverse("sitemap"))
    assert response.status_code == 200
    xml = ElementTree.fromstring(response.content)  # noqa: S314 -- our own Django XML.
    ns = {
        "s": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "x": "http://www.w3.org/1999/xhtml",
    }
    urls = [node.text for node in xml.findall("s:url/s:loc", ns)]
    assert "http://testserver/en/" in urls and "http://testserver/ur/" in urls
    assert "http://testserver/ur/programs/education-support/" in urls
    assert all(
        "/app/" not in url and "tree-plantation" not in url and "BR-QTA-01" not in url
        for url in urls
    )
    assert {node.attrib["hreflang"] for node in xml.findall("s:url/x:link", ns)} == {
        "en",
        "ur",
        "x-default",
    }


def test_robots_and_private_noindex(client, sample_data):
    response = client.get(reverse("robots"))
    assert response.status_code == 200
    for value in [
        "Disallow: /en/app/",
        "Disallow: /ur/app/",
        "Disallow: /accounts/",
        "http://testserver/sitemap.xml",
    ]:
        assert value in response.text
    assert (
        Metadata(client.get(reverse("account-login")).text).meta["robots"]
        == "noindex, nofollow"
    )
    client.force_login(User.objects.get(role="CONTENT_EDITOR"))
    assert (
        Metadata(client.get(reverse("content-list")).text).meta["robots"]
        == "noindex, nofollow"
    )
