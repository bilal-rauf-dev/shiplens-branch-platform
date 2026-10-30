from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import Role, User
from apps.audit.models import AuditLog
from apps.cms import selectors, services
from apps.cms.models import ContentItem, ContentTranslation
from apps.cms.templatetags.cms import render_cms
from apps.core import clock as business_clock
from apps.core.exceptions import InvalidTransition

pytestmark = pytest.mark.django_db


def test_t_cms_states(editor, copy):
    item = services.create(editor, type="PROGRAM", translations=copy)
    for operation, status in [
        ("publish", "PUBLISHED"),
        ("publish", "PUBLISHED"),
        ("unpublish", "DRAFT"),
        ("archive", "ARCHIVED"),
        ("restore", "DRAFT"),
        ("publish", "PUBLISHED"),
        ("archive", "ARCHIVED"),
    ]:
        item = services.transition(editor, item.pk, operation)
        assert item.status == status
    with pytest.raises(InvalidTransition):
        services.transition(editor, item.pk, "publish")
    with pytest.raises(InvalidTransition):
        services.update(editor, item.pk, translations=copy)
    with pytest.raises(InvalidTransition):
        services.transition(editor, item.pk, "delete")
    assert AuditLog.objects.filter(entity_type="contentitem").count() == 8


def test_t_cms_live_snapshot(editor, copy, clock):
    item = services.create(
        editor, type="PROGRAM", translations=copy, image_path="img/cms/learning.svg"
    )
    services.transition(editor, item.pk, "publish")
    clock.shift(timedelta(hours=1))
    copy["en"]["title"] = "Working-only title"
    item = services.update(
        editor, item.pk, translations=copy, image_path="img/cms/care.svg"
    )
    assert item.has_unpublished_changes
    assert item.updated_at == business_clock.now()
    visible = selectors.localize(item.published_snapshot, "en")
    assert visible["title"] == "Learning together"
    assert visible["image_path"] == "img/cms/learning.svg"
    item = services.transition(editor, item.pk, "publish")
    assert not item.has_unpublished_changes
    assert item.published_snapshot["en"]["title"] == "Working-only title"


@pytest.mark.parametrize(
    "locale,field", [("en", "title"), ("en", "body_md"), ("ur", "title")]
)
def test_t_cms_publish_guard(editor, copy, locale, field):
    copy[locale][field] = ""
    item = services.create(
        editor, type="PROGRAM", translations=copy, slug="publish-guard"
    )
    with pytest.raises(ValidationError):
        services.transition(editor, item.pk, "publish")
    item.refresh_from_db()
    assert item.status == "DRAFT" and not item.published_snapshot


def test_urdu_empty_body_falls_back_with_note(editor, copy):
    copy["ur"]["body_md"] = ""
    item = services.create(editor, type="PROGRAM", translations=copy)
    item = services.transition(editor, item.pk, "publish")
    visible = selectors.localize(item.published_snapshot, "ur")
    assert visible["english_only"] and visible["fallback_note"]
    assert visible["body_html"] == item.published_snapshot["en"]["body_html"]


@pytest.mark.parametrize("slug", ["ab", "Bad-Slug", "bad_slug", "x" * 81, "bad\nslug"])
def test_t_cms_slug(editor, copy, slug):
    with pytest.raises(ValidationError):
        services.create(editor, type="PROGRAM", translations=copy, slug=slug)


def test_slug_is_unique_per_type(editor, copy):
    item = services.create(editor, type="PROGRAM", translations=copy)
    assert item.slug == "learning-together"
    with pytest.raises(ValidationError):
        services.create(editor, type="PROGRAM", translations=copy)
    services.create(editor, type="PAGE_SECTION", translations=copy)
    with pytest.raises(IntegrityError), transaction.atomic():
        ContentTranslation.objects.create(content=item, locale="en")


def test_t_cms_event_dates(editor, copy):
    now = business_clock.now()
    with pytest.raises(ValidationError):
        services.create(
            editor,
            type="EVENT",
            translations=copy,
            event_start=now,
            event_end=now - timedelta(hours=1),
        )
    with pytest.raises(ValidationError):
        services.create(editor, type="EVENT", translations=copy)
    item = services.create(
        editor, type="EVENT", translations=copy, event_start=now, event_end=now
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        ContentItem.objects.filter(pk=item.pk).update(
            event_end=now - timedelta(hours=1)
        )


@pytest.mark.parametrize(
    "payload",
    [
        "<script>alert(1)</script>",
        '<img src=x onerror="alert(1)">',
        "[bad](javascript:alert(1))",
        '<iframe src="https://example.com"></iframe>',
    ],
)
def test_t_sec_xss_cms(editor, copy, payload):
    copy["en"]["body_md"] = payload
    item = services.create(editor, type="PROGRAM", translations=copy)
    html = str(render_cms(item.translations.get(locale="en").body_html))
    for bad in ("<script", "onerror", "javascript:", "<iframe", "<img"):
        assert bad not in html
    assert "<script" not in str(render_cms("<script>bad</script>"))


def test_allowed_links_receive_noopener(editor, copy):
    copy["en"]["body_md"] = "[Visit](https://example.org)"
    item = services.create(editor, type="PROGRAM", translations=copy)
    assert 'rel="noopener"' in item.translations.get(locale="en").body_html


def test_cms_audit_failure_rolls_back(editor, copy):
    with patch(
        "apps.cms.services.audit.record", side_effect=RuntimeError("audit unavailable")
    ):
        with pytest.raises(RuntimeError):
            services.create(editor, type="PROGRAM", translations=copy)
    assert not ContentItem.objects.exists()


def test_cms_other_roles_cannot_mutate(copy):
    user = User.objects.create_user(
        email="lead@example.org", full_name="Branch Lead", role=Role.BRANCH_LEAD
    )
    with pytest.raises(PermissionDenied):
        services.create(user, type="PROGRAM", translations=copy)


@pytest.mark.parametrize("missing_locale", ["en", "ur"])
def test_cms_update_requires_both_languages_without_changes(
    editor, copy, clock, missing_locale
):
    item = services.create(editor, type="PROGRAM", translations=copy)
    services.transition(editor, item.pk, "publish")
    before_item = ContentItem.objects.values().get(pk=item.pk)
    before_translations = list(
        ContentTranslation.objects.filter(content=item).order_by("locale").values()
    )
    before_audit = AuditLog.objects.count()
    clock.shift(timedelta(hours=1))
    translations = {
        locale: {**values, "title": "This change must not be saved"}
        for locale, values in copy.items()
        if locale != missing_locale
    }
    with pytest.raises(
        ValueError, match=f"Missing translation locale: {missing_locale}"
    ):
        services.update(editor, item.pk, translations=translations, slug="changed-slug")
    assert ContentItem.objects.values().get(pk=item.pk) == before_item
    assert (
        list(
            ContentTranslation.objects.filter(content=item).order_by("locale").values()
        )
        == before_translations
    )
    assert AuditLog.objects.count() == before_audit
