from django import forms
from django.utils.translation import gettext_lazy as _


class PeriodForm(forms.Form):
    period = forms.DateField(
        label=_("Period"),
        input_formats=["%Y-%m"],
        widget=forms.DateInput(format="%Y-%m", attrs={"type": "month"}),
    )
