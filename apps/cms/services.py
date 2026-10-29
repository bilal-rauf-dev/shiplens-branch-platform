"""Lock working copies and publish snapshots in the same audit transaction."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps import audit
from apps.accounts.permissions import require, scope_queryset
from apps.cms import selectors
from apps.cms.models import ContentItem, ContentStatus, ContentTranslation, ContentType
from apps.cms.sanitizing import from_markdown
from apps.core import clock
from apps.core.exceptions import InvalidTransition

EDITABLE = (
    "slug",
    "event_start",
    "event_end",
    "location_en",
    "location_ur",
    "branch",
    "image_path",
    "sort_order",
)
TRANSITIONS = {
    "publish": {"DRAFT": "PUBLISHED", "PUBLISHED": "PUBLISHED"},
    "unpublish": {"PUBLISHED": "DRAFT"},
    "archive": {"DRAFT": "ARCHIVED", "PUBLISHED": "ARCHIVED"},
    "restore": {"ARCHIVED": "DRAFT"},
}
ACTIONS = {
    "publish": "content.publish",
    "unpublish": "content.unpublish",
    "archive": "content.archive",
    "restore": "content.restore",
}
EVENTS = {
    "publish": "content.published",
    "unpublish": "content.unpublished",
    "archive": "content.archived",
    "restore": "content.restored",
}


def _validate(item):
    if item.type == ContentType.EVENT and (not item.event_start or not item.event_end):
        raise ValidationError(_("Events need a start and end time."))
    item.full_clean()


def _translations(item, translations):
    for locale in ("en", "ur"):
        values = translations.get(locale, {})
        row, _created = ContentTranslation.objects.get_or_create(
            content=item, locale=locale
        )
        for field in ("title", "summary", "body_md"):
            setattr(row, field, values.get(field, ""))
        row.body_html = from_markdown(row.body_md)  # BR-123
        row.full_clean()
        row.save()


@transaction.atomic
def create(actor, *, type, translations, **fields):
    """Create a draft, deriving a valid per-type slug from its English title. BR-120."""
    require(actor, "content.create")
    values = {key: value for key, value in fields.items() if key in EDITABLE}
    values["slug"] = (
        values.get("slug") or slugify(translations.get("en", {}).get("title", ""))[:80]
    )
    item = ContentItem(type=type, created_by=actor, updated_by=actor, **values)
    _validate(item)
    item.save()
    _translations(item, translations)
    audit.record(
        actor, "content.created", entity=item, after=selectors.working_snapshot(item)
    )
    return item


@transaction.atomic
def update(actor, pk, *, translations, **fields):
    """Only the working copy changes; published output stays frozen until publish."""
    require(actor, "content.update")
    item = get_object_or_404(
        scope_queryset(
            actor, "content.update", ContentItem.objects.select_for_update()
        ),
        pk=pk,
    )
    if item.status == ContentStatus.ARCHIVED:
        raise InvalidTransition(_("Restore archived content before editing."))
    before = selectors.working_snapshot(item)
    for field in EDITABLE:
        if field in fields:
            setattr(item, field, fields[field])
    item.updated_by, item.updated_at = actor, clock.now()
    item.has_unpublished_changes = item.status == ContentStatus.PUBLISHED
    _validate(item)
    item.save()
    _translations(item, translations)
    audit.record(
        actor,
        "content.updated",
        entity=item,
        before=before,
        after=selectors.working_snapshot(item),
    )
    return item


@transaction.atomic
def transition(actor, pk, operation):
    """BR-121: publish EN title/body plus UR title; every other move uses the table."""
    if operation not in TRANSITIONS:
        raise InvalidTransition(_("Unknown content transition."))
    action = ACTIONS[operation]
    require(actor, action)
    item = get_object_or_404(
        scope_queryset(actor, action, ContentItem.objects.select_for_update()), pk=pk
    )
    target = TRANSITIONS[operation].get(item.status)
    if target is None:
        raise InvalidTransition(_("This content transition is not available."))
    before = {"status": item.status, "published_at": item.published_at}
    if operation == "publish":
        snapshot = selectors.working_snapshot(item)
        if not (
            snapshot["en"]["title"].strip()
            and snapshot["en"]["body_html"].strip()
            and snapshot["ur"]["title"].strip()
        ):
            raise ValidationError(
                _("Publishing needs an English title and body and an Urdu title.")
            )
        if (
            ContentItem.objects.filter(
                type=item.type,
                status=ContentStatus.PUBLISHED,
                published_snapshot__meta__slug=item.slug,
            )
            .exclude(pk=item.pk)
            .exists()
        ):
            raise ValidationError(_("That published slug is already in use."))
        item.published_snapshot = snapshot
        item.published_at = clock.now()
        item.has_unpublished_changes = False
    item.status, item.updated_by, item.updated_at = target, actor, clock.now()
    if target != ContentStatus.PUBLISHED:
        item.has_unpublished_changes = False
    item.save()
    audit.record(
        actor,
        EVENTS[operation],
        entity=item,
        before=before,
        after={"status": target, "published_at": item.published_at},
        metadata={"snapshot": item.published_snapshot}
        if operation == "publish"
        else {},
    )
    return item
