from django import forms
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Role
from apps.accounts.permissions import scope_queryset
from apps.audit import selectors
from apps.branches.models import Branch


class AuditFilterForm(forms.Form):
    date_from = forms.DateField(
        label=_("From date (PKT)"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_to = forms.DateField(
        label=_("To date (PKT)"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    actor = forms.CharField(label=_("Actor email"), max_length=254, required=False)
    role = forms.ChoiceField(
        label=_("Actor role"),
        choices=[("", _("All roles")), *Role.choices],
        required=False,
    )
    action = forms.ChoiceField(label=_("Action"), required=False)
    entity_type = forms.ChoiceField(label=_("Entity type"), required=False)
    entity = forms.CharField(
        label=_("Entity ID or label"), max_length=120, required=False
    )
    branch = forms.ModelChoiceField(
        label=_("Branch"),
        queryset=Branch.objects.none(),
        required=False,
        empty_label=_("All branches"),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["action"].choices = selectors.action_choices()
        self.fields["entity_type"].choices = [
            ("", _("All entity types")),
            *[(value, value) for value in selectors.entity_types()],
        ]
        self.fields["branch"].queryset = scope_queryset(
            user, "branch.list", Branch.objects.order_by("code")
        )

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("date_from"), cleaned.get("date_to")
        if start and end and start > end:
            self.add_error(
                "date_to", _("The end date must be on or after the start date.")
            )
        return cleaned
