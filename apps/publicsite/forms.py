from django import forms
from django.utils.translation import gettext_lazy as _

from apps.branches.models import City
from apps.branches.selectors import public_branches
from apps.core.forms import Form


class CityFilterForm(Form):
    city = forms.ModelChoiceField(
        label=_("City"),
        to_field_name="code",
        required=False,
        empty_label=_("All cities"),
        queryset=City.objects.none(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["city"].queryset = (
            City.objects.filter(branches__in=public_branches())
            .distinct()
            .order_by("code")
        )
