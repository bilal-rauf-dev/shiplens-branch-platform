from django import forms
from django.utils.translation import gettext_lazy as _

from apps.cms.models import ILLUSTRATIONS, ContentStatus, ContentType
from apps.core.forms import Form


class ContentFilterForm(Form):
    type = forms.ChoiceField(
        choices=ContentType.choices, required=False, label=_("Type")
    )
    status = forms.ChoiceField(
        choices=[("", _("All statuses")), *ContentStatus.choices],
        required=False,
        label=_("Status"),
    )


class ContentForm(Form):
    type = forms.ChoiceField(label=_("Type"), choices=ContentType.choices)
    slug = forms.RegexField(
        label=_("Slug"),
        regex=r"\A[a-z0-9-]{3,80}\Z",
        max_length=80,
        required=False,
        help_text=_("Leave blank to generate it from the English title."),
    )
    sort_order = forms.IntegerField(label=_("Sort order"), initial=0)
    image_path = forms.ChoiceField(
        label=_("Illustration"),
        choices=ILLUSTRATIONS,
        required=False,
        widget=forms.RadioSelect,
    )
    event_start = forms.DateTimeField(
        label=_("Event start (PKT)"),
        required=False,
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}
        ),
    )
    event_end = forms.DateTimeField(
        label=_("Event end (PKT)"),
        required=False,
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}
        ),
    )
    location_en = forms.CharField(
        label=_("English location"), max_length=200, required=False
    )
    location_ur = forms.CharField(
        label=_("Urdu location"),
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"dir": "rtl", "lang": "ur"}),
    )
    title_en = forms.CharField(label=_("English title"), max_length=150, required=False)
    summary_en = forms.CharField(
        label=_("English summary"), max_length=300, required=False
    )
    body_en = forms.CharField(
        label=_("English body (Markdown)"), required=False, widget=forms.Textarea
    )
    title_ur = forms.CharField(label=_("Urdu title"), max_length=150, required=False)
    summary_ur = forms.CharField(
        label=_("Urdu summary"), max_length=300, required=False
    )
    body_ur = forms.CharField(
        label=_("Urdu body (Markdown)"), required=False, widget=forms.Textarea
    )

    def __init__(self, *args, item=None, **kwargs):
        self.item = item
        super().__init__(*args, **kwargs)
        for name in ("title_ur", "summary_ur", "body_ur"):
            self.fields[name].widget.attrs.update(dir="rtl", lang="ur")
        if item:
            self.fields["type"].disabled = True
            self.fields["slug"].required = True
            self.fields["slug"].help_text = _("Use a stable public URL.")

    def clean(self):
        values = super().clean()
        if values.get("type") == ContentType.EVENT:
            for name in ("event_start", "event_end"):
                if not values.get(name):
                    self.add_error(name, _("This field is required for events."))
        start, end = values.get("event_start"), values.get("event_end")
        if start and end and end < start:
            self.add_error("event_end", _("The event must end on or after its start."))
        return values

    def service_data(self):
        """Pass explicit working-copy fields, with no status or actor input."""
        values = self.cleaned_data
        return {
            "translations": {
                locale: {
                    "title": values[f"title_{locale}"],
                    "summary": values[f"summary_{locale}"],
                    "body_md": values[f"body_{locale}"],
                }
                for locale in ("en", "ur")
            },
            **{
                name: values[name]
                for name in (
                    "type",
                    "slug",
                    "sort_order",
                    "image_path",
                    "event_start",
                    "event_end",
                    "location_en",
                    "location_ur",
                )
            },
        }
