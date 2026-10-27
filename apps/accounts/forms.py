from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.accounts import selectors, services
from apps.accounts.models import Role, User
from apps.core import rules


class LoginForm(forms.Form):
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "username"}),
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        cleaned = super().clean()
        if "email" in cleaned and "password" in cleaned:
            cleaned["email"] = User.objects.normalize_email(cleaned["email"])
            self.user = services.authenticate_user(
                self.request, cleaned["email"], cleaned["password"]
            )
            if self.user is None:
                raise ValidationError(_("Email or password is incorrect."))
        return cleaned


class ChangePasswordForm(PasswordChangeForm):
    """Use Django's password validation; persistence stays in the account service."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        minimum = rules.get("password_min_length")
        for name in ("new_password1", "new_password2"):
            self.fields[name].widget.attrs["minlength"] = minimum


class UserCreateForm(forms.Form):
    email = forms.EmailField(label=_("Email"), max_length=254)
    full_name = forms.CharField(label=_("Full name"), max_length=100)
    role = forms.ChoiceField(label=_("Role"), choices=Role.choices)


class UserEditForm(forms.Form):
    full_name = forms.CharField(label=_("Full name"), max_length=100)
    role = forms.ChoiceField(label=_("Role"), choices=Role.choices)


class BranchAssignmentForm(forms.Form):
    branch_id = forms.TypedChoiceField(label=_("Branch"), coerce=int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch_id"].choices = [
            (branch.pk, f"{branch.code} · {branch.name_en}")
            for branch in selectors.assignable_branches()
        ]


class SystemSettingsForm(forms.Form):
    collection_lock_days = forms.IntegerField(label=_("Collection lock days"))
    allow_submit_current_week = forms.BooleanField(
        label=_("Allow submission during the current week"),
        required=False,
    )
    min_volunteer_age = forms.IntegerField(label=_("Minimum volunteer age"))
    apply_rate_per_hour = forms.IntegerField(label=_("Applications per hour per IP"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key in ("collection_lock_days", "min_volunteer_age", "apply_rate_per_hour"):
            minimum, maximum = rules.get(f"{key}_min"), rules.get(f"{key}_max")
            self.fields[key].widget.attrs.update({"min": minimum, "max": maximum})
            self.fields[key].help_text = _("Allowed range: %(min)s–%(max)s.") % {
                "min": minimum,
                "max": maximum,
            }

    def clean(self):
        cleaned = super().clean()
        if not self.errors:
            services.validate_settings(cleaned)
        return cleaned
