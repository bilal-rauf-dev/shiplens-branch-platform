"""Working-copy reads are separate from published snapshot reads."""

from django.utils.translation import gettext as _

from apps.cms.models import ContentItem, ContentStatus


def items():
    return ContentItem.objects.prefetch_related("translations").order_by(
        "type", "sort_order", "slug"
    )


def working_snapshot(item):
    return {
        **{
            row.locale: {
                "title": row.title,
                "summary": row.summary,
                "body_md": row.body_md,
                "body_html": row.body_html,
            }
            for row in item.translations.all()
        },
        "meta": {
            "slug": item.slug,
            "image_path": item.image_path,
            "sort_order": item.sort_order,
            "location_en": item.location_en,
            "location_ur": item.location_ur,
            "branch_id": item.branch_id,
            "event_start": item.event_start.isoformat() if item.event_start else None,
            "event_end": item.event_end.isoformat() if item.event_end else None,
        },
    }


def localize(snapshot, locale):
    """BR-121: an absent Urdu body falls back to English with a visible note."""
    english = snapshot.get("en", {})
    chosen = snapshot.get(locale, english)
    fallback = locale == "ur" and not chosen.get("body_html")
    return {
        **snapshot.get("meta", {}),
        **chosen,
        "body_html": english.get("body_html", "")
        if fallback
        else chosen.get("body_html", ""),
        "english_only": fallback,
        "fallback_note": _("English only") if fallback else "",
    }


def published_items():
    return ContentItem.objects.filter(status=ContentStatus.PUBLISHED).order_by(
        "published_snapshot__meta__sort_order", "pk"
    )
