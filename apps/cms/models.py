from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core import clock


class ContentType(models.TextChoices):
    PAGE_SECTION = "PAGE_SECTION", _("Page section")
    PROGRAM = "PROGRAM", _("Program")
    EVENT = "EVENT", _("Event")


class ContentStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    PUBLISHED = "PUBLISHED", _("Published")
    ARCHIVED = "ARCHIVED", _("Archived")


ILLUSTRATIONS = [
    ("", _("No illustration")),
    ("img/cms/learning.svg", _("Learning")),
    ("img/cms/community.svg", _("Community")),
    ("img/cms/care.svg", _("Care")),
    ("img/cms/growth.svg", _("Growth")),
    ("img/cms/hero-volunteers.svg", _("Volunteers")),
    ("img/cms/education.svg", _("Education")),
    ("img/cms/rations.svg", _("Rations")),
    ("img/cms/health.svg", _("Health")),
    ("img/cms/trees.svg", _("Trees")),
    ("img/cms/orientation.svg", _("Orientation")),
]


class ContentItem(models.Model):
    type = models.CharField(_("type"), max_length=16, choices=ContentType.choices)
    slug = models.CharField(
        _("slug"),
        max_length=80,
        validators=[
            RegexValidator(
                r"\A[a-z0-9-]{3,80}\Z",
                _("Use 3–80 lowercase letters, digits or hyphens."),
            )
        ],
    )
    status = models.CharField(
        _("status"),
        max_length=12,
        choices=ContentStatus.choices,
        default=ContentStatus.DRAFT,
    )
    has_unpublished_changes = models.BooleanField(default=False)
    published_snapshot = models.JSONField(default=dict, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    event_start = models.DateTimeField(_("event start"), null=True, blank=True)
    event_end = models.DateTimeField(_("event end"), null=True, blank=True)
    location_en = models.CharField(_("English location"), max_length=200, blank=True)
    location_ur = models.CharField(_("Urdu location"), max_length=200, blank=True)
    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.RESTRICT, null=True, blank=True
    )
    image_path = models.CharField(
        _("illustration"), max_length=200, choices=ILLUSTRATIONS, blank=True
    )
    sort_order = models.IntegerField(_("sort order"), default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="created_content",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="updated_content",
    )
    created_at = models.DateTimeField(default=clock.now)
    updated_at = models.DateTimeField(default=clock.now)

    class Meta:
        db_table = "content_items"
        constraints = [
            models.UniqueConstraint(
                fields=["type", "slug"], name="content_type_slug_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(type__in=ContentType.values),
                name="content_type_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=ContentStatus.values),
                name="content_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(event_end__gte=models.F("event_start")),
                name="content_event_dates_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(slug__regex=r"^[a-z0-9-]{3,80}$"),
                name="content_slug_valid",
            ),
        ]

    def __str__(self):
        return self.slug


class ContentTranslation(models.Model):
    content = models.ForeignKey(
        ContentItem, on_delete=models.CASCADE, related_name="translations"
    )
    locale = models.CharField(max_length=5, choices=[("en", "English"), ("ur", "اردو")])
    title = models.CharField(_("title"), max_length=150, blank=True)
    summary = models.CharField(_("summary"), max_length=300, blank=True)
    body_md = models.TextField(_("body (Markdown)"), blank=True)
    body_html = models.TextField(blank=True)

    class Meta:
        db_table = "content_translations"
        constraints = [
            models.UniqueConstraint(
                fields=["content", "locale"], name="content_locale_unique"
            )
        ]

    def __str__(self):
        return f"{self.content_id} · {self.locale} · {self.title}"
