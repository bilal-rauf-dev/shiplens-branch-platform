"""Public submissions and HR decisions use explicit business transactions."""

import hashlib
import secrets

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django_ratelimit.core import is_ratelimited

from apps import audit
from apps.accounts.permissions import require, scope_queryset
from apps.audit.context import request_context
from apps.branches.models import Branch, BranchStatus
from apps.core import clock, ids, rules
from apps.core.exceptions import InvalidTransition
from apps.core.models import IdSequence
from apps.core.net import client_ip_key
from apps.volunteers import selectors
from apps.volunteers.models import (
    Application,
    ApplicationStatus,
    Member,
    MemberStatus,
    Team,
    VolunteerRole,
)

APPLICATION_FIELDS = (
    "full_name",
    "email",
    "phone",
    "date_of_birth",
    "guardian_consent",
    "interests",
    "availability",
    "motivation",
    "preferred_language",
)


def _public_audit(action, **fields):
    """Public events retain request correlation without an IP or user identity."""
    context = request_context.get() or {}
    token = request_context.set(
        {
            "ip": None,
            "user_agent": "",
            "request_id": context.get("request_id"),
            "authenticated": False,
        }
    )
    try:
        audit.record(None, action, **fields)
    finally:
        request_context.reset(token)


def application_rate_limited(request):
    """Serialize django-ratelimit's database-cache increments across workers."""
    with transaction.atomic():
        # DatabaseCache.incr is read/modify/write. A dedicated existing-table
        # lock row makes both checks atomic; its last_value deliberately stays 0.
        IdSequence.objects.get_or_create(key="application:rate-limit")
        IdSequence.objects.select_for_update().get(pk="application:rate-limit")
        hourly = is_ratelimited(
            request,
            group="application-hour",
            key=client_ip_key,
            rate=f"{rules.get('apply_rate_per_hour')}/h",
            method="POST",
            increment=True,
        )
        daily = is_ratelimited(
            request,
            group="application-day",
            key=client_ip_key,
            rate=f"{rules.get('apply_rate_per_day')}/d",
            method="POST",
            increment=True,
        )
        return hourly or daily


def spam_reason(data):
    """Check the honeypot and signed clock value before validating applicant PII."""
    if data.get("website"):
        return "honeypot"
    try:
        payload = signing.loads(data.get("render_token", ""), salt="apply-form")
        elapsed = clock.now().timestamp() - payload["rendered_at"]
        if (
            not rules.get("form_min_seconds")
            <= elapsed
            <= rules.get("form_max_seconds")
        ):
            return "timing"
    except (signing.BadSignature, TypeError, KeyError):
        return "timing"
    return None


def discard_spam(reason):
    """Log a reason without form data, then return a plausible generic reference."""
    with transaction.atomic():
        _public_audit("application.spam_blocked", metadata={"reason": reason})
    return f"APP-{clock.today().year}-{secrets.randbelow(100000):05d}"


def submit_application(cleaned_data, request_ip):
    """Re-check the branch, reserve a reference and flag duplicates. BR-004, BR-052."""
    with transaction.atomic():
        if not cleaned_data.get("privacy_consent"):
            raise ValidationError(
                {"privacy_consent": _("You must agree to the privacy notice.")}
            )
        branch = Branch.objects.select_for_update(no_key=True).get(
            pk=cleaned_data["preferred_branch"].pk
        )
        if branch.status not in {BranchStatus.ACTIVE, BranchStatus.FORMING}:
            raise ValidationError(
                {"preferred_branch": _("This branch is not accepting applications.")}
            )
        year = clock.today().year
        number = ids.next_value(f"application:{year}")
        existing_application = selectors.duplicate_application(
            cleaned_data["email"], cleaned_data["phone"]
        )
        existing_member = selectors.duplicate_member(
            cleaned_data["email"], cleaned_data["phone"]
        )
        application = Application(
            **{field: cleaned_data[field] for field in APPLICATION_FIELDS},
            reference=f"APP-{year}-{number:05d}",
            preferred_branch=branch,
            consent_at=clock.now(),
            possible_duplicate=bool(existing_application or existing_member),
            duplicate_of_application=existing_application,
            duplicate_of_member=existing_member,
            ip_hash=hashlib.sha256(
                ((request_ip or "") + settings.SECRET_KEY).encode()
            ).hexdigest(),
            created_at=clock.now(),
            updated_at=clock.now(),
        )
        application.full_clean()
        application.save(force_insert=True)
        _public_audit(
            "application.submitted",
            entity=application,
            branch_id=branch.pk,
            after={
                "reference": application.reference,
                "preferred_branch_id": branch.pk,
            },
        )
        return application


def _lock_pending_application(actor, application_id, action):
    """Scope before lookup and check the state after taking the row lock. BR-053."""
    require(actor, action)
    application = get_object_or_404(
        scope_queryset(
            actor, action, Application.objects.select_for_update(no_key=True)
        ),
        pk=application_id,
    )
    require(actor, action, application)
    if application.status != ApplicationStatus.PENDING:
        raise InvalidTransition(_("This application has already been decided."))
    return application


def accept_application(actor, application_id, *, team_id=None, role_id):
    """Accept once and create a member with both audits atomically. BR-003, BR-054."""
    with transaction.atomic():
        application = _lock_pending_application(
            actor, application_id, "application.accept"
        )
        branch = Branch.objects.select_for_update(no_key=True).get(
            pk=application.preferred_branch_id
        )
        if branch.status == BranchStatus.CLOSED:
            raise InvalidTransition(
                _("This branch is closed and cannot accept applicants.")
            )
        team = None
        if team_id is not None:
            team = (
                Team.objects.select_for_update(no_key=True)
                .filter(pk=team_id, branch_id=branch.pk)
                .first()
            )
            if team is None:
                raise ValidationError(
                    {"team_id": _("Choose a team from this application's branch.")}
                )
        role = VolunteerRole.objects.filter(pk=role_id).first()
        if role is None:
            raise ValidationError({"role_id": _("Choose an existing volunteer role.")})
        current = clock.now()
        today = clock.today()
        number = ids.next_value(f"member:{today.year}")
        # BR-055: give reviewers a useful error before the database constraint.
        if (
            Member.objects.exclude(status=MemberStatus.LEFT)
            .filter(email__iexact=application.email)
            .exists()
        ):
            raise ValidationError(
                {"email": _("A current member already uses this email address.")}
            )
        member = Member(
            member_id=f"M-{today.year}-{number:05d}",
            application=application,
            branch=branch,
            team=team,
            volunteer_role=role,
            full_name=application.full_name,
            email=application.email,
            phone=application.phone,
            status=MemberStatus.ACTIVE,
            joined_on=today,
            created_by=actor,
            updated_by=actor,
            created_at=current,
            updated_at=current,
        )
        member.full_clean()
        member.save(force_insert=True)
        application.status = ApplicationStatus.ACCEPTED
        application.member = member
        application.decided_by = actor
        application.decided_at = current
        application.updated_at = current
        application.full_clean()
        application.save(
            update_fields=["status", "member", "decided_by", "decided_at", "updated_at"]
        )
        audit.record(
            actor,
            "application.accepted",
            entity=application,
            branch_id=branch.pk,
            before={"status": ApplicationStatus.PENDING, "member_id": None},
            after={"status": application.status, "member_id": member.pk},
        )
        audit.record(
            actor,
            "member.created",
            entity=member,
            branch_id=branch.pk,
            after={
                "member_id": member.member_id,
                "application_id": application.pk,
                "branch_id": branch.pk,
                "team_id": member.team_id,
                "volunteer_role_id": role.pk,
                "status": member.status,
                "joined_on": member.joined_on,
            },
        )
        return member


def decline_application(actor, application_id, reason):
    """Record an HR decision and its internal reason from Pending only. BR-053."""
    with transaction.atomic():
        application = _lock_pending_application(
            actor, application_id, "application.decline"
        )
        reason = reason.strip()
        minimum = rules.get("application_decline_reason_min_length")
        maximum = rules.get("application_decline_reason_max_length")
        if not minimum <= len(reason) <= maximum:
            raise ValidationError(
                {
                    "reason": _(
                        "Give a reason between %(minimum)s and %(maximum)s characters."
                    )
                    % {"minimum": minimum, "maximum": maximum}
                }
            )
        application.status = ApplicationStatus.DECLINED
        application.decision_note = reason
        application.decided_by = actor
        application.decided_at = clock.now()
        application.updated_at = application.decided_at
        application.full_clean()
        application.save(
            update_fields=[
                "status",
                "decision_note",
                "decided_by",
                "decided_at",
                "updated_at",
            ]
        )
        audit.record(
            actor,
            "application.declined",
            entity=application,
            branch_id=application.preferred_branch_id,
            before={"status": ApplicationStatus.PENDING, "decision_note": ""},
            after={"status": application.status, "decision_note": reason},
        )
        return application


def reassign_branch(actor, application_id, branch_id):
    """Move a scoped Pending application to any open branch. BR-045, BR-053."""
    with transaction.atomic():
        application = _lock_pending_application(
            actor, application_id, "application.reassign_branch"
        )
        target = (
            Branch.objects.select_for_update(no_key=True).filter(pk=branch_id).first()
        )
        if target is None or target.status not in {
            BranchStatus.ACTIVE,
            BranchStatus.FORMING,
        }:
            raise ValidationError(
                {"branch_id": _("Choose an Active or Forming branch.")}
            )
        previous_branch_id = application.preferred_branch_id
        application.preferred_branch = target
        application.updated_at = clock.now()
        application.full_clean()
        application.save(update_fields=["preferred_branch", "updated_at"])
        audit.record(
            actor,
            "application.reassigned",
            entity=application,
            branch_id=target.pk,
            before={"preferred_branch_id": previous_branch_id},
            after={"preferred_branch_id": target.pk},
        )
        return application
