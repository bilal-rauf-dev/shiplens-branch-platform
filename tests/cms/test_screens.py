import pytest
from django.test import Client
from django.urls import reverse

from apps.cms import services
from apps.cms.models import ContentItem

pytestmark = pytest.mark.django_db


@pytest.fixture
def item(editor, copy):
    return services.create(editor, type="PROGRAM", translations=copy)


def payload():
    return {
        "type": "PROGRAM",
        "sort_order": 0,
        "slug": "education-support",
        "title_en": "Education support",
        "summary_en": "Learn with us.",
        "body_en": "## Learning\n\nLocal tutoring.",
        "title_ur": "تعلیم میں تعاون",
        "image_path": "img/cms/learning.svg",
    }


def test_editor_saves_and_previews_working_copy(client, editor, item):
    client.force_login(editor)
    response = client.get(reverse("content-edit", args=[item.pk]))
    assert response.status_code == 200
    for marker in [
        'id="cms-tab-en"',
        'id="cms-tab-ur"',
        'name="title_ur"',
        'dir="rtl"',
        'lang="ur"',
        'class="cms-image-picker"',
    ]:
        assert marker in response.text
    assert "<script" not in response.text
    assert (
        client.post(reverse("content-edit", args=[item.pk]), payload()).status_code
        == 302
    )
    response = client.get(reverse("content-preview", args=[item.pk]))
    assert response.status_code == 200
    assert "Preview — not published" in response.text
    assert "<h2>Learning</h2>" in response.text
    item.refresh_from_db()
    assert item.status == "DRAFT"


def test_create_ignores_forged_status_actor_and_branch(client, editor):
    client.force_login(editor)
    response = client.post(
        reverse("content-create"),
        {**payload(), "status": "PUBLISHED", "created_by": 999, "branch": 999},
    )
    assert response.status_code == 302
    item = ContentItem.objects.get()
    assert item.status == "DRAFT" and item.created_by == editor and item.branch is None


def test_transitions_confirm_get_and_post_redirect_get(client, editor, item):
    client.force_login(editor)
    url = reverse("content-publish", args=[item.pk])
    assert client.get(url).status_code == 200
    item.refresh_from_db()
    assert item.status == "DRAFT"
    response = client.post(url)
    assert response.status_code == 302 and response.url == reverse("content-list")
    response = client.get(reverse("content-unpublish", args=[item.pk]))
    assert "btn--error" in response.text
    response = client.post(reverse("content-restore", args=[item.pk]))
    assert response.status_code == 409


def test_publish_guard_is_shown_on_confirmation(client, editor, item):
    client.force_login(editor)
    values = payload()
    values["title_ur"] = ""
    client.post(reverse("content-edit", args=[item.pk]), values)
    response = client.post(reverse("content-publish", args=[item.pk]))
    assert response.status_code == 400
    assert 'role="alert"' in response.text


def test_invalid_event_and_static_image_choices(client, editor):
    client.force_login(editor)
    response = client.post(
        reverse("content-create"),
        {**payload(), "type": "EVENT", "image_path": "https://example.org/image.png"},
    )
    assert response.status_code == 400
    assert set(response.context["form"].errors) >= {
        "event_start",
        "event_end",
        "image_path",
    }
    assert not ContentItem.objects.exists()


def test_content_tabs_and_unpublished_changes_chip(client, editor, item, copy):
    services.transition(editor, item.pk, "publish")
    services.update(editor, item.pk, translations=copy)
    client.force_login(editor)
    response = client.get(reverse("content-list"), {"type": "PROGRAM"})
    assert "Unpublished changes" in response.text
    assert "Published" in response.text
    assert item in list(response.context["items"])
    assert not client.get(reverse("content-list"), {"type": "EVENT"}).context["items"]


def test_content_post_keeps_csrf_protection(editor, item):
    client = Client(enforce_csrf_checks=True)
    client.force_login(editor)
    assert client.post(reverse("content-publish", args=[item.pk])).status_code == 403
