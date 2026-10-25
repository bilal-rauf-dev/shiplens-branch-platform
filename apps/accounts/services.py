"""Authentication writes and password changes share explicit transaction boundaries."""

from datetime import timedelta

from django.contrib import auth
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.accounts.signals import password_changed
from apps.core import clock, rules


def authenticate_user(request, email, password):
    """Keep failure tracking and future auth audit signals in the same transaction."""
    with transaction.atomic():
        return auth.authenticate(request, username=email, password=password)


def start_session_deadline(request):
    """Store login and activity times with a fixed absolute deadline."""
    current = clock.now()
    request.session["auth_started_at"] = current.timestamp()
    request.session["auth_last_activity_at"] = current.timestamp()
    request.session.set_expiry(
        current + timedelta(seconds=rules.get("session_absolute_seconds"))
    )


def sign_in(request, user):
    """Rotate the session through Django login and set the fixed lifetime."""
    with transaction.atomic():
        auth.login(request, user)
        start_session_deadline(request)


def sign_out(request):
    """Flush the session and emit Django's logout signal inside the transaction."""
    with transaction.atomic():
        auth.logout(request)


def change_password(request, old_password, new_password):
    """Lock and change the caller's password, preserving their session."""
    with transaction.atomic():
        user = (
            User.objects.select_for_update()
            .filter(pk=request.user.pk, is_active=True)
            .first()
        )
        if user is None or user.is_demo:
            raise PermissionDenied(_("This account's password cannot be changed."))
        if not user.check_password(old_password):
            raise ValidationError(_("Your current password is incorrect."))
        validate_password(new_password, user=user)
        user.set_password(new_password)
        user.must_change_password = False
        user.updated_at = clock.now()
        user.save(update_fields=["password", "must_change_password", "updated_at"])
        auth.update_session_auth_hash(request, user)
        request.user = user
        password_changed.send(sender=User, request=request, user=user)
        return user
