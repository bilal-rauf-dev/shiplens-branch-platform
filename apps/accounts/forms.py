from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.accounts import services
from apps.accounts.models import User


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
