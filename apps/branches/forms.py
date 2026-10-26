"""Explicit public form fields for branch and city administration."""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.branches.models import BranchStatus, City


class BranchFilterForm(forms.Form):
    city = forms.ModelChoiceField(
        label=_("City"), queryset=City.objects.order_by("code"), required=False
    )
    status = forms.ChoiceField(
        label=_("Status"),
        choices=[("", _("All statuses")), *BranchStatus.choices],
        required=False,
    )


class BranchCreateForm(forms.Form):
    city = forms.ModelChoiceField(
        label=_("City"), queryset=City.objects.order_by("code")
    )
    name_en = forms.CharField(label=_("English name"), max_length=100)
    name_ur = forms.CharField(label=_("Urdu name"), max_length=100)
    address_en = forms.CharField(
        label=_("English address"), max_length=250, required=False
    )
    address_ur = forms.CharField(
        label=_("Urdu address"), max_length=250, required=False
    )
    phone = forms.RegexField(
        label=_("Phone"), regex=r"\A\+[1-9][0-9]{1,14}\Z", max_length=16, required=False
    )
    email = forms.EmailField(label=_("Email"), max_length=254, required=False)


class BranchEditForm(forms.Form):
    name_en = forms.CharField(label=_("English name"), max_length=100)
    name_ur = forms.CharField(label=_("Urdu name"), max_length=100)
    address_en = forms.CharField(
        label=_("English address"), max_length=250, required=False
    )
    address_ur = forms.CharField(
        label=_("Urdu address"), max_length=250, required=False
    )
    phone = forms.RegexField(
        label=_("Phone"), regex=r"\A\+[1-9][0-9]{1,14}\Z", max_length=16, required=False
    )
    email = forms.EmailField(label=_("Email"), max_length=254, required=False)


class CityCreateForm(forms.Form):
    code = forms.RegexField(label=_("Code"), regex=r"\A[A-Z]{3}\Z", max_length=3)
    name_en = forms.CharField(label=_("English name"), max_length=60)
    name_ur = forms.CharField(label=_("Urdu name"), max_length=60)


class CityEditForm(forms.Form):
    name_en = forms.CharField(label=_("English name"), max_length=60)
    name_ur = forms.CharField(label=_("Urdu name"), max_length=60)
