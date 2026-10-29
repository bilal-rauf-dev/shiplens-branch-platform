import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.models import User
from apps.cms import services
from apps.cms.models import ContentItem
from apps.volunteers.models import Application, Member

pytestmark = pytest.mark.django_db
PATHS = [
    "",
    "about/",
    "programs/",
    "programs/education-support/",
    "branches/",
    "branches/BR-KHI-01/",
    "events/",
    "events/health-camp-lahore/",
    "get-involved/",
    "contact/",
    "privacy/",
]


@pytest.mark.parametrize("language", ["en", "ur"])
@pytest.mark.parametrize("path", PATHS)
def test_t_pub_pages(client, sample_data, language, path):
    with CaptureQueriesContext(connection) as queries:
        response = client.get(f"/{language}/{path}")
    assert response.status_code == 200
    assert f'lang="{language}"' in response.text
    assert len(queries) <= 6, [(q["sql"]) for q in queries]


def test_t_cms_public_only_published(client, sample_data):
    editor = User.objects.get(role="CONTENT_EDITOR")
    item = ContentItem.objects.get(slug="education-support")
    translations = {
        row.locale: {
            "title": "PRIVATE WORKING TITLE",
            "body_md": row.body_md,
            "summary": row.summary,
        }
        for row in item.translations.all()
    }
    services.update(
        editor, item.pk, translations=translations, image_path="img/cms/growth.svg"
    )
    response = client.get("/en/programs/education-support/")
    assert (
        "Education support" in response.text
        and "PRIVATE WORKING TITLE" not in response.text
    )
    services.transition(editor, item.pk, "archive")
    assert client.get("/en/programs/education-support/").status_code == 404
    assert "Education support" not in client.get("/en/programs/").text


def test_t_pub_no_leak(client, sample_data):
    editor = User.objects.get(role="CONTENT_EDITOR")
    archived = services.create(
        editor,
        type="PROGRAM",
        slug="archived-story",
        translations={
            "en": {"title": "PRIVATE ARCHIVED STORY", "body_md": "Private history."},
            "ur": {"title": "نجی محفوظ کہانی"},
        },
    )
    services.transition(editor, archived.pk, "archive")
    private = list(Member.objects.values_list("email", flat=True))
    private += list(Application.objects.values_list("email", flat=True))
    private += list(User.objects.values_list("email", flat=True))
    private += list(Member.objects.values_list("full_name", flat=True))
    private += [
        row.title
        for item in ContentItem.objects.exclude(status="PUBLISHED")
        for row in item.translations.all()
    ]
    for language in ("en", "ur"):
        for path in PATHS:
            text = client.get(f"/{language}/{path}").text
            assert "Tree plantation draft" not in text
            assert "/app/" not in text
            assert all(value not in text for value in private)
    assert client.get("/en/programs/tree-plantation/").status_code == 404


def test_public_content_stays_public_when_staff_is_signed_in(client, sample_data):
    client.force_login(User.objects.get(role="SUPER_ADMIN"))
    text = client.get("/en/").text
    assert "/app/" not in text
    assert "staff-rail" not in text


def test_t_pub_branch_visibility(client, sample_data):
    response = client.get("/en/branches/")
    for code in ("BR-KHI-01", "BR-LHE-01", "BR-ISB-01", "BR-PEW-01"):
        assert code in response.text
    assert "BR-QTA-01" not in response.text
    assert client.get("/en/branches/BR-QTA-01/").status_code == 404
    text = client.get("/en/branches/", {"city": "KHI"}).text
    assert "BR-KHI-01" in text and "BR-LHE-01" not in text


@pytest.mark.parametrize("language", ["en", "ur"])
def test_public_pages_have_no_script_tags(client, sample_data, language):
    for path in PATHS:
        assert "<script" not in client.get(f"/{language}/{path}").text


def test_events_move_between_upcoming_and_past_by_business_date(
    client, sample_data, clock
):
    response = client.get("/en/events/")
    assert len(response.context["upcoming"]) == 3 and len(response.context["past"]) == 1
    clock.move_to("2026-11-08T00:00:00+05:00")
    response = client.get("/en/events/")
    assert len(response.context["upcoming"]) == 2 and len(response.context["past"]) == 2


def test_language_switch_uses_translated_next_and_cookie(client, sample_data):
    response = client.post(
        reverse("set_language"), {"language": "ur", "next": "/ur/branches/?city=KHI"}
    )
    assert response.status_code == 302 and response.url == "/ur/branches/?city=KHI"
    assert response.cookies["django_language"].value == "ur"
    assert client.get(reverse("set_language")).status_code == 405


def test_public_invalid_city_is_a_visible_form_error(client, sample_data):
    response = client.get("/en/branches/", {"city": "UNKNOWN"})
    assert response.status_code == 400
    assert response.context["form"].errors
