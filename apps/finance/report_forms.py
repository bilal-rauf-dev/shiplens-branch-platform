from django import forms
from django.core.validators import MaxLengthValidator
from django.utils.translation import gettext_lazy as _

from apps.accounts.permissions import scope_queryset
from apps.branches.models import Branch
from apps.core import rules
from apps.finance.models import ReportStatus
from apps.finance.report_fields import REPORT_FIELDS


class ReportFilterForm(forms.Form):
    branch = forms.ModelChoiceField(
        label=_("Branch"),
        queryset=Branch.objects.none(),
        required=False,
        empty_label=_("All branches"),
    )
    status = forms.ChoiceField(
        label=_("Status"),
        choices=[("", _("All statuses")), *ReportStatus.choices],
        required=False,
    )
    week_from = forms.DateField(
        label=_("Week from"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    week_to = forms.DateField(
        label=_("Week to"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = scope_queryset(
            user, "report.list", Branch.objects.order_by("code"), branch_field="pk"
        )

    def clean(self):
        values = super().clean()
        if (
            values.get("week_from")
            and values.get("week_to")
            and values["week_from"] > values["week_to"]
        ):
            self.add_error(
                "week_to", _("The end date must be on or after the start date.")
            )
        return values


class ReportReviewForm(forms.Form):
    expected_revision = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    comment = forms.CharField(
        label=_("Review comment"), required=False, widget=forms.Textarea
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        maximum = rules.get("report_return_comment_max_length")
        self.fields["comment"].validators.append(MaxLengthValidator(maximum))
        self.fields["comment"].widget.attrs["maxlength"] = maximum


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
