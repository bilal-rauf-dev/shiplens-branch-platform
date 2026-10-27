from datetime import timedelta

from django import forms
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.utils.translation import gettext_lazy as _

from apps.core import clock, rules
from apps.finance import selectors
from apps.finance.models import Collection, CollectionMethod, CollectionState
from apps.volunteers.models import Member


class CollectionFilterForm(forms.Form):
    date_from = forms.DateField(
        label=_("From date"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_to = forms.DateField(
        label=_("To date"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    method = forms.ChoiceField(
        label=_("Method"),
        choices=[("", _("All methods")), *CollectionMethod.choices],
        required=False,
    )
    state = forms.ChoiceField(
        label=_("State"),
        choices=[
            ("", _("All states")),
            ("UNSENT", _("Unsent")),
            *CollectionState.choices,
        ],
        required=False,
    )

    def clean(self):
        cleaned = super().clean()
        if (
            cleaned.get("date_from")
            and cleaned.get("date_to")
            and cleaned["date_from"] > cleaned["date_to"]
        ):
            self.add_error(
                "date_to", _("The end date must be on or after the start date.")
            )
        return cleaned


class TransferSelectionForm(forms.Form):
    collections = forms.ModelMultipleChoiceField(
        label=_("Collections"),
        queryset=Collection.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["collections"].queryset = selectors.unsent(user)

    def clean_collections(self):
        items = self.cleaned_data["collections"]
        if len({item.branch_id for item in items}) != 1:
            raise forms.ValidationError(_("Choose collections from one branch only."))
        return items


class TransferForm(forms.Form):
    collections = forms.ModelMultipleChoiceField(
        label=_("Collections"),
        queryset=Collection.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )
    transfer_date = forms.DateField(
        label=_("Transfer date"), widget=forms.DateInput(attrs={"type": "date"})
    )
    bank_reference = forms.CharField(label=_("Bank reference"), max_length=50)
    note = forms.CharField(label=_("Note"), required=False, widget=forms.Textarea)

    def __init__(self, *args, branch, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["collections"].queryset = Collection.objects.filter(
            branch=branch, transfer__isnull=True, voided_at__isnull=True
        ).order_by("collection_date", "pk")
        self.fields["transfer_date"].widget.attrs["max"] = clock.today().isoformat()
        minimum = rules.get("transfer_bank_reference_min_length")
        maximum = rules.get("transfer_bank_reference_max_length")
        self.fields["bank_reference"].validators.extend(
            [MinLengthValidator(minimum), MaxLengthValidator(maximum)]
        )
        self.fields["bank_reference"].widget.attrs.update(
            {"minlength": minimum, "maxlength": maximum}
        )

    def clean(self):
        cleaned = super().clean()
        selected, transfer_date = (
            cleaned.get("collections"),
            cleaned.get("transfer_date"),
        )
        if transfer_date and (
            transfer_date > clock.today()
            or (
                selected
                and transfer_date < max(item.collection_date for item in selected)
            )
        ):
            self.add_error(
                "transfer_date",
                _(
                    "Choose a transfer date between the latest "
                    "collection date and today."
                ),
            )
        return cleaned


class VoidCollectionForm(forms.Form):
    reason = forms.CharField(label=_("Void reason"), widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        minimum = rules.get("collection_void_reason_min_length")
        maximum = rules.get("collection_void_reason_max_length")
        self.fields["reason"].validators.extend(
            [MinLengthValidator(minimum), MaxLengthValidator(maximum)]
        )
        self.fields["reason"].widget.attrs.update(
            {"minlength": minimum, "maxlength": maximum}
        )


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
