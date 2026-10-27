from datetime import timedelta

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core import clock, rules
from apps.finance.models import CollectionMethod
from apps.volunteers.models import Member


class CollectionForm(forms.Form):
    collection_date = forms.DateField(
        label=_("Collection date"), widget=forms.DateInput(attrs={"type": "date"})
    )
    amount = forms.DecimalField(
        label=_("Amount (PKR)"),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
    )
    method = forms.ChoiceField(label=_("Method"), choices=CollectionMethod.choices)
    receipt_no = forms.RegexField(
        label=_("Receipt number"),
        regex=r"\A[A-Za-z0-9\-/]{1,30}\Z",
        max_length=30,
        widget=forms.TextInput(attrs={"pattern": r"[A-Za-z0-9\-/]{1,30}"}),
    )
    collected_by = forms.ModelChoiceField(
        label=_("Collected by"), queryset=Member.objects.none(), required=False
    )
    source_note = forms.CharField(
        label=_("Source note"), max_length=200, required=False
    )

    def __init__(self, *args, branch, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["collected_by"].queryset = Member.objects.filter(
            branch=branch
        ).order_by("full_name")
        today = clock.today()
        self.fields["collection_date"].widget.attrs.update(
            {
                "min": (
                    today - timedelta(days=rules.get("collection_lock_days"))
                ).isoformat(),
                "max": today.isoformat(),
            }
        )
        self.fields["amount"].widget.attrs["max"] = str(rules.get("max_collection"))

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if not 0 < amount <= rules.get("max_collection"):
            raise forms.ValidationError(_("Choose an amount within the allowed range."))
        return amount

    def clean_collection_date(self):
        value = self.cleaned_data["collection_date"]
        today = clock.today()
        if (
            not today - timedelta(days=rules.get("collection_lock_days"))
            <= value
            <= today
        ):
            raise forms.ValidationError(
                _("Choose a date within the allowed collection window.")
            )
        return value
