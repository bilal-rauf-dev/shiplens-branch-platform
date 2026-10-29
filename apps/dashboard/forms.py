from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import Form


class PeriodForm(Form):
    period = forms.DateField(
        label=_("Period"),
        input_formats=["%Y-%m"],
        widget=forms.DateInput(format="%Y-%m", attrs={"type": "month"}),
    )
