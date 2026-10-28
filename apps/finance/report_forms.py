from django import forms

from apps.finance.report_fields import REPORT_FIELDS


class ReportNarrativeForm(forms.Form):
    """Build only the explicitly registered narrative fields. BR-084."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, specification in REPORT_FIELDS.items():
            options = {
                key: value for key, value in specification.items() if key != "type"
            }
            if specification["type"] == "text":
                self.fields[name] = forms.CharField(widget=forms.Textarea, **options)
            else:
                self.fields[name] = forms.IntegerField(**options)
