"""Authentication writes and password changes share explicit transaction boundaries."""

import secrets
from datetime import timedelta

from django.contrib import auth
from django.contrib.auth.password_validation import validate_password
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.views.decorators.debug import sensitive_variables
from django_ratelimit.core import is_ratelimited

from apps import audit
from apps.accounts import selectors
from apps.accounts.models import Role, User, UserBranchAssignment
from apps.accounts.permissions import invalidate_assignment_snapshot, require
from apps.accounts.signals import password_changed
from apps.branches.models import Branch, BranchStatus
from apps.core import clock, rules
from apps.core.models import IdSequence, SystemSetting
from apps.core.net import client_ip_key


def login_rate_limited(request):
    """Limit all login POSTs from one resolved IP, independently of email."""
    with transaction.atomic():
        # DatabaseCache.incr is not atomic. Hold this fixed mutex row around
        # both django-ratelimit calls, then release it before password hashing.
        IdSequence.objects.get_or_create(key="auth:rate-limit")
        IdSequence.objects.select_for_update().get(pk="auth:rate-limit")
        minute = is_ratelimited(
            request,
            group="login-minute",
            key=client_ip_key,
            rate=f"{rules.get('login_rate_per_minute')}/m",
            method="POST",
            increment=True,
        )
        day = is_ratelimited(
            request,
            group="login-day",
            key=client_ip_key,
            rate=f"{rules.get('login_rate_per_day')}/d",
            method="POST",
            increment=True,
        )
        limited = minute or day
        if limited:
            audit.record(
                None, "auth.rate_limited", metadata={"reason": "client_ip_limit"}
            )
        return limited


def authenticate_user(request, email, password):
    """Keep failure tracking and auth audit signals in the same transaction."""
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
        user.updated_at = clock.now()
        user.save(update_fields=["updated_at"])
        start_session_deadline(request)


def sign_out(request):
    """Flush the session and emit Django's logout signal inside the transaction."""
    with transaction.atomic():
        auth.logout(request)


def change_password(request, old_password, new_password):
    """Lock and change the caller's password, preserving their session."""
    with transaction.atomic():
        user = (
            User.objects.select_for_update(no_key=True)
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


def assign_branch(actor, user, branch):
    """Assign a branch once, serializing assignments with changes to the user's role."""
    with transaction.atomic():
        actor = _lock_admin_actor(actor, "assignment.manage")
        user = User.objects.select_for_update(no_key=True).get(pk=user.pk)
        _editable_user(user)
        if user.role not in {Role.BRANCH_LEAD, Role.HR_LEAD}:
            raise ValidationError(
                _("Only Branch Leads and HR Leads can be assigned branches.")
            )
        branch = Branch.objects.select_for_update(no_key=True).get(pk=branch.pk)
        if branch.status == BranchStatus.CLOSED:  # BR-014
            raise ValidationError(_("Closed branches cannot receive assignments."))
        assignment, _created = UserBranchAssignment.objects.get_or_create(
            user=user, branch=branch, defaults={"created_by": actor}
        )
        invalidate_assignment_snapshot(user.pk)
        if _created:
            user.updated_at = clock.now()
            user.save(update_fields=["updated_at"])
            audit.record(
                actor,
                "assignment.added",
                entity=assignment,
                branch_id=branch.pk,
                after={"user_id": user.pk, "branch_id": branch.pk},
            )
        return assignment


def _lock_admin_actor(actor, action):
    """Serialize admin writes, then re-check the actor's current persisted role."""
    require(actor, action)
    # NO KEY UPDATE permits audit inserts' foreign-key checks while these locks
    # are held. All admin writers take the same ordered locks before target locks.
    admins = list(
        User.objects.select_for_update(no_key=True)
        .filter(role=Role.SUPER_ADMIN, is_active=True)
        .order_by("pk")
    )
    current = next((admin for admin in admins if admin.pk == actor.pk), None)
    require(current, action)
    return current


def _editable_user(user):
    if user.is_demo:
        raise PermissionDenied(_("Demo accounts cannot be edited."))


def _user_fields(user):
    return {"full_name": user.full_name, "role": user.role, "is_active": user.is_active}


def _guard_last_admin(user, role, active):
    if user.role == Role.SUPER_ADMIN and user.is_active:
        if role != Role.SUPER_ADMIN or not active:
            if (
                not User.objects.filter(role=Role.SUPER_ADMIN, is_active=True)
                .exclude(pk=user.pk)
                .exists()
            ):
                raise ValidationError(
                    _("The last active Super Admin cannot be demoted or deactivated.")
                )


def _remove_assignment(actor, assignment):
    audit.record(
        actor,
        "assignment.removed",
        entity=assignment,
        branch_id=assignment.branch_id,
        before={"user_id": assignment.user_id, "branch_id": assignment.branch_id},
    )
    # Remove only the access-control link; the user, branch and audit history remain.
    assignment.delete()
    invalidate_assignment_snapshot(assignment.user_id)


@sensitive_variables()
def create_user(actor, *, email, full_name, role):
    """Create an active account and return its temporary password for one response."""
    with transaction.atomic():
        actor = _lock_admin_actor(actor, "user.create")
        if actor.is_demo and role == Role.SUPER_ADMIN:
            raise PermissionDenied(_("Demo Super Admins cannot create Super Admins."))
        temporary = secrets.token_urlsafe(rules.get("temporary_password_bytes"))
        user = User.objects.create_user(
            email=email,
            full_name=full_name,
            role=role,
            password=temporary,
            must_change_password=True,
            updated_at=clock.now(),
        )
        audit.record(
            actor,
            "user.created",
            entity=user,
            after={"email": user.email, **_user_fields(user)},
        )
        return user, temporary


def update_user(actor, user, *, full_name, role):
    """Edit explicit fields without demo edits or losing the last active SA."""
    with transaction.atomic():
        actor = _lock_admin_actor(actor, "user.update")
        user = User.objects.select_for_update(no_key=True).get(pk=user.pk)
        _editable_user(user)
        if actor.is_demo and role == Role.SUPER_ADMIN and user.role != Role.SUPER_ADMIN:
            raise PermissionDenied(_("Demo Super Admins cannot create Super Admins."))
        _guard_last_admin(user, role, user.is_active)
        before = _user_fields(user)
        user.full_name = full_name
        user.role = role
        user.updated_at = clock.now()
        user.full_clean()
        if role not in {Role.BRANCH_LEAD, Role.HR_LEAD}:
            for assignment in user.branch_assignments.order_by("pk"):
                _remove_assignment(actor, assignment)
        user.save(update_fields=["full_name", "role", "updated_at"])
        audit.record(
            actor, "user.updated", entity=user, before=before, after=_user_fields(user)
        )
        return user


def set_user_active(actor, user, *, active):
    """Change active status, protect the last admin and revoke disabled sessions."""
    with transaction.atomic():
        actor = _lock_admin_actor(actor, "user.update")
        user = User.objects.select_for_update(no_key=True).get(pk=user.pk)
        _editable_user(user)
        if type(active) is not bool:
            raise ValidationError(_("Active must be true or false."))
        _guard_last_admin(user, user.role, active)
        before = {"is_active": user.is_active}
        user.is_active = active
        user.updated_at = clock.now()
        user.save(update_fields=["is_active", "updated_at"])
        if not active:
            Session.objects.filter(
                session_key__in=selectors.user_session_keys(user)
            ).delete()
        audit.record(
            actor,
            "user.reactivated" if active else "user.deactivated",
            entity=user,
            before=before,
            after={"is_active": active},
        )
        return user


@sensitive_variables()
def reset_temporary_password(actor, user):
    """Issue a secret once and revoke sessions; never reset demo accounts."""
    with transaction.atomic():
        actor = _lock_admin_actor(actor, "user.reset_password")
        user = User.objects.select_for_update(no_key=True).get(pk=user.pk)
        _editable_user(user)
        temporary = secrets.token_urlsafe(rules.get("temporary_password_bytes"))
        validate_password(temporary, user=user)
        user.set_password(temporary)
        user.must_change_password = True
        user.updated_at = clock.now()
        user.save(update_fields=["password", "must_change_password", "updated_at"])
        Session.objects.filter(
            session_key__in=selectors.user_session_keys(user)
        ).delete()
        audit.record(
            actor,
            "auth.password_reset_issued",
            entity=user,
            after={"must_change_password": True},
        )
        return user, temporary


def remove_branch_assignment(actor, user, branch_id):
    """Revoke a branch access link while retaining an audit record of the removal."""
    with transaction.atomic():
        actor = _lock_admin_actor(actor, "assignment.manage")
        user = User.objects.select_for_update(no_key=True).get(pk=user.pk)
        _editable_user(user)
        assignment = user.branch_assignments.filter(branch_id=branch_id).first()
        if assignment is not None:
            _remove_assignment(actor, assignment)
            user.updated_at = clock.now()
            user.save(update_fields=["updated_at"])
        return user


EDITABLE_SETTINGS = (
    "collection_lock_days",
    "allow_submit_current_week",
    "min_volunteer_age",
    "apply_rate_per_hour",
)


def validate_settings(values):
    """Validate the same whitelist and bounds for forms and direct service callers."""
    errors = {}
    if set(values) != set(EDITABLE_SETTINGS):
        raise ValidationError(_("Provide exactly the four editable settings."))
    for key in EDITABLE_SETTINGS:
        value = values[key]
        if key == "allow_submit_current_week":
            valid = type(value) is bool
        else:
            valid = type(value) is int and rules.get(
                f"{key}_min"
            ) <= value <= rules.get(f"{key}_max")
        if not valid:
            errors[key] = _("Enter a value within the allowed range.")
    if errors:
        raise ValidationError(errors)


def update_settings(actor, **values):
    """Persist validated overrides with one audit event in the same transaction."""
    with transaction.atomic():
        actor = _lock_admin_actor(actor, "settings.update")
        validate_settings(values)
        before = {key: rules.get(key) for key in EDITABLE_SETTINGS}
        for key in EDITABLE_SETTINGS:
            SystemSetting.objects.update_or_create(
                key=key,
                defaults={
                    "value": values[key],
                    "updated_by": actor,
                    "updated_at": clock.now(),
                },
            )
        audit.record(
            actor,
            "settings.updated",
            entity_type="system_settings",
            before=before,
            after=values,
        )


def set_preferred_language(actor, language):
    """Save the caller's language preference and its audit event together."""
    require(actor, "account.set_language")
    with transaction.atomic():
        user = (
            User.objects.select_for_update().filter(pk=actor.pk, is_active=True).first()
        )
        if user is None:
            raise PermissionDenied
        if user.preferred_language == language:
            return
        before = {"preferred_language": user.preferred_language}
        user.preferred_language = language
        user.updated_at = clock.now()
        user.save(update_fields=["preferred_language", "updated_at"])
        audit.record(
            actor,
            "user.updated",
            entity=user,
            before=before,
            after={"preferred_language": language},
        )
