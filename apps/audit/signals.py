"""Translate framework authentication signals into sanitized audit events."""

from axes.signals import user_locked_out
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db import transaction
from django.dispatch import receiver

from apps.accounts.backends import login_email
from apps.accounts.signals import password_changed
from apps.audit.services import record


@receiver(user_logged_in, dispatch_uid="audit.login_succeeded")
def login_succeeded(sender, request, user, **kwargs):
    with transaction.atomic():
        record(user, "auth.login_succeeded")


@receiver(user_login_failed, dispatch_uid="audit.login_failed")
def login_failed(sender, credentials, request=None, **kwargs):
    email = login_email(request, credentials)
    with transaction.atomic():
        record(None, "auth.login_failed", metadata={"email": email[:254]})


@receiver(user_logged_out, dispatch_uid="audit.logout")
def logout(sender, request, user, **kwargs):
    with transaction.atomic():
        record(user, "auth.logout")


@receiver(user_locked_out, dispatch_uid="audit.locked_out")
def locked_out(sender, request, username, **kwargs):
    with transaction.atomic():
        record(None, "auth.locked_out", metadata={"email": username[:254]})


@receiver(password_changed, dispatch_uid="audit.password_changed")
def changed_password(sender, request, user, **kwargs):
    with transaction.atomic():
        record(user, "auth.password_changed")
