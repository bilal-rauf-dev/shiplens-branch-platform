"""Public content is read exclusively from published snapshots."""

from datetime import datetime

from django.shortcuts import get_object_or_404

from apps.cms import selectors as cms
from apps.core import clock


def cards(locale, type=None):
    queryset = cms.published_items()
    if type:
        queryset = queryset.filter(type=type)
    return [payload(item, locale) for item in queryset]


def payload(item, locale):
    value = cms.localize(item.published_snapshot, locale)
    value["type"] = item.type
    for key in ("event_start", "event_end"):
        value[key] = (
            datetime.fromisoformat(value[key]).astimezone(clock.KARACHI)
            if value.get(key)
            else None
        )
    value["location"] = value.get(f"location_{locale}") or value.get("location_en", "")
    return value


def detail(type, slug, locale):
    return payload(
        get_object_or_404(
            cms.published_items(), type=type, published_snapshot__meta__slug=slug
        ),
        locale,
    )


def event_groups(rows):
    today = clock.today()
    upcoming = sorted(
        (row for row in rows if row["event_start"].date() >= today),
        key=lambda row: row["event_start"],
    )
    past = sorted(
        (row for row in rows if row["event_start"].date() < today),
        key=lambda row: row["event_start"],
        reverse=True,
    )
    return upcoming, past
