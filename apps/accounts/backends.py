"""Authenticate email identities without Django's group or superuser permissions."""

from django.contrib.auth.backends import BaseBackend

from apps.accounts.models import User


class EmailBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get("email")
        if not email or password is None:
            return None
        user = User.objects.filter(
            email__iexact=User.objects.normalize_email(email)
        ).first()
        if user is None:
            # Hash even for an unknown email to reduce timing differences.
            User().set_password(password)
            return None
        if user.check_password(password) and user.is_active:
            return user
        return None

    def get_user(self, user_id):
        return User.objects.filter(pk=user_id, is_active=True).first()


def login_email(request, credentials=None):
    """Give Axes the same normalized email key used by authentication."""
    credentials = credentials or {}
    email = (
        credentials.get("email")
        or credentials.get("username")
        or request.POST.get("email", "")
    )
    return User.objects.normalize_email(email)
