"""Public submissions and HR decisions use explicit business transactions."""

import hashlib
import re
import secrets

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
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

MEMBER_TRANSITIONS = {
    (MemberStatus.ACTIVE, "deactivate"): MemberStatus.INACTIVE,
    (MemberStatus.INACTIVE, "reactivate"): MemberStatus.ACTIVE,
    (MemberStatus.ACTIVE, "mark_left"): MemberStatus.LEFT,
    (MemberStatus.INACTIVE, "mark_left"): MemberStatus.LEFT,
    (MemberStatus.LEFT, "reinstate"): MemberStatus.ACTIVE,
}


def import_member(
    actor=None, *, branch, team, volunteer_role, full_name, email, phone, joined_on
):
    """Import a spreadsheet member with the shared yearly counter and system audit.

    This service is for the historical importer, not an HTTP creation endpoint.
    Subsequent status changes still use transition_member. BR-054, BR-055.
    """
    with transaction.atomic():
        if actor is not None:
            require(actor, "member.update", branch)
        Branch.objects.select_for_update(no_key=True).get(pk=branch.pk)
        if team is not None and team.branch_id != branch.pk:
            raise ValidationError(_("Choose a team from this member's branch."))
        if joined_on != clock.today():
            raise ValidationError(_("Import members at their historical joining date."))
        number = ids.next_value(f"member:{joined_on.year}")
        member = Member(
            member_id=f"M-{joined_on.year}-{number:05d}",
            branch=branch,
            team=team,
            volunteer_role=volunteer_role,
            full_name=full_name,
            email=email.strip().lower(),
            phone=phone,
            joined_on=joined_on,
            created_by=actor,
            updated_by=actor,
            created_at=clock.now(),
            updated_at=clock.now(),
        )
        member.full_clean()
        member.save(force_insert=True)
        audit.record(
            actor,
            "member.created",
            entity=member,
            branch_id=branch.pk,
            after={"member_id": member.member_id, "branch_id": branch.pk},
            metadata={"source": "spreadsheet import"},
        )
        return member


def _locked_member(actor, member_id, action):
    require(actor, action)
    return get_object_or_404(
        scope_queryset(actor, action, Member.objects.select_for_update(no_key=True)),
        pk=member_id,
    )


def update_member(actor, member_id, *, team_id, role_id, phone, notes):
    """Edit only mutable member fields within scope, preserving identifiers. BR-056."""
    with transaction.atomic():
        member = _locked_member(actor, member_id, "member.update")
        team = None
        if team_id is not None:
            team = (
                Team.objects.select_for_update(no_key=True)
                .filter(pk=team_id, branch_id=member.branch_id)
                .first()
            )
            if team is None or (not team.is_active and team.pk != member.team_id):
                raise ValidationError(
                    {"team_id": _("Choose an active team from this member's branch.")}
                )
        role = (
            VolunteerRole.objects.select_for_update(no_key=True)
            .filter(pk=role_id)
            .first()
        )
        if role is None or (not role.is_active and role.pk != member.volunteer_role_id):
            raise ValidationError({"role_id": _("Choose an active volunteer role.")})
        if re.fullmatch(r"\+923[0-9]{9}", phone) is None:
            raise ValidationError(
                {"phone": _("Enter a Pakistani mobile number in international format.")}
            )
        before = {
            "team_id": member.team_id,
            "volunteer_role_id": member.volunteer_role_id,
            "phone": member.phone,
            "notes": member.notes,
        }
        member.team, member.volunteer_role = team, role
        member.phone, member.notes = phone, notes.strip()
        member.updated_by, member.updated_at = actor, clock.now()
        member.full_clean()
        member.save(
            update_fields=[
                "team",
                "volunteer_role",
                "phone",
                "notes",
                "updated_by",
                "updated_at",
            ]
        )
        audit.record(
            actor,
            "member.updated",
            entity=member,
            branch_id=member.branch_id,
            before=before,
            after={
                "team_id": member.team_id,
                "volunteer_role_id": member.volunteer_role_id,
                "phone": member.phone,
                "notes": member.notes,
            },
        )
        return member


def transition_member(actor, member_id, action, *, left_on=None, reason=""):
    """Apply the explicit member status table under a row lock. BR-055, BR-058."""
    permission = "member.reinstate" if action == "reinstate" else "member.update"
    with transaction.atomic():
        member = _locked_member(actor, member_id, permission)
        target = MEMBER_TRANSITIONS.get((member.status, action))
        if target is None:
            raise InvalidTransition(
                _("This action is not available for the member's current status.")
            )
        if action == "mark_left" and (left_on is None or left_on < member.joined_on):
            raise ValidationError(
                {"left_on": _("The leaving date must be on or after the joining date.")}
            )
        if action == "reinstate":
            if not reason.strip():
                raise ValidationError(
                    {"reason": _("Give a reason for reinstating this member.")}
                )
            if (
                Member.objects.exclude(status=MemberStatus.LEFT)
                .exclude(pk=member.pk)
                .filter(email__iexact=member.email)
                .exists()
            ):
                raise ValidationError(
                    _("A current member already uses this email address.")
                )
        before = {"status": member.status, "left_on": member.left_on}
        member.status = target
        member.left_on = left_on if target == MemberStatus.LEFT else None
        member.updated_by, member.updated_at = actor, clock.now()
        member.full_clean()
        try:
            with transaction.atomic():
                member.save(
                    update_fields=["status", "left_on", "updated_by", "updated_at"]
                )
        except IntegrityError as error:
            if (
                getattr(error.__cause__.diag, "constraint_name", None)
                == "members_current_email_unique"
            ):
                raise ValidationError(
                    _("A current member already uses this email address.")
                ) from error
            raise
        audit.record(
            actor,
            "member.reinstated" if action == "reinstate" else "member.status_changed",
            entity=member,
            branch_id=member.branch_id,
            before=before,
            after={"status": member.status, "left_on": member.left_on},
            metadata={"reason": reason.strip()} if action == "reinstate" else {},
        )
        return member


def _managed_branch(actor, branch_id):
    """Lock branches before teams, matching the acceptance service's lock order."""
    require(actor, "team.manage")
    return get_object_or_404(
        scope_queryset(
            actor,
            "team.manage",
            Branch.objects.select_for_update(no_key=True),
            branch_field="pk",
        ),
        pk=branch_id,
    )


def _lock_team(actor, team_id):
    require(actor, "team.manage")
    scoped = scope_queryset(actor, "team.manage", Team.objects.all())
    team = get_object_or_404(scoped, pk=team_id)
    _managed_branch(actor, team.branch_id)
    return get_object_or_404(scoped.select_for_update(no_key=True), pk=team_id)


def _validate_team_name(team):
    # BR-057: the branch lock serializes competing creates and renames.
    if (
        Team.objects.filter(branch_id=team.branch_id, name__iexact=team.name)
        .exclude(pk=team.pk)
        .exists()
    ):
        raise ValidationError(
            {"name": _("A team with this name already exists in this branch.")}
        )
    team.full_clean()


def create_team(actor, branch_id, *, name):
    """Create a team in a managed branch, retaining case-insensitive uniqueness."""
    with transaction.atomic():
        branch = _managed_branch(actor, branch_id)
        team = Team(branch=branch, name=name.strip())
        _validate_team_name(team)
        team.save(force_insert=True)
        audit.record(
            actor,
            "team.created",
            entity=team,
            branch_id=branch.pk,
            after={"branch_id": branch.pk, "name": team.name, "is_active": True},
        )
        return team


def rename_team(actor, team_id, *, name):
    """Rename a scoped team without changing its branch or member references."""
    with transaction.atomic():
        team = _lock_team(actor, team_id)
        before = {"name": team.name}
        team.name = name.strip()
        _validate_team_name(team)
        team.save(update_fields=["name"])
        audit.record(
            actor,
            "team.updated",
            entity=team,
            branch_id=team.branch_id,
            before=before,
            after={"name": team.name},
        )
        return team


def deactivate_team(actor, team_id):
    """Stop new team assignments while preserving existing member links."""
    with transaction.atomic():
        team = _lock_team(actor, team_id)
        before = {"is_active": team.is_active}
        team.is_active = False
        team.save(update_fields=["is_active"])
        audit.record(
            actor,
            "team.updated",
            entity=team,
            branch_id=team.branch_id,
            before=before,
            after={"is_active": False},
        )
        return team


def create_volunteer_role(actor, *, name_en, name_ur, sort_order):
    """Allocate a stable role code and add bilingual labels in one transaction."""
    with transaction.atomic():
        require(actor, "volunteer_role.manage")
        number = ids.next_value("volunteer-role")
        role = VolunteerRole(
            code=f"ROLE-{number:05d}",
            name_en=name_en.strip(),
            name_ur=name_ur.strip(),
            sort_order=sort_order,
        )
        role.full_clean()
        role.save(force_insert=True)
        audit.record(
            actor,
            "volunteer_role.created",
            entity=role,
            after={
                "code": role.code,
                "name_en": role.name_en,
                "name_ur": role.name_ur,
                "sort_order": role.sort_order,
                "is_active": True,
            },
        )
        return role


def update_volunteer_role(actor, role_id, *, name_en, name_ur, sort_order):
    """Edit role labels and ordering without accepting a submitted code or state."""
    with transaction.atomic():
        require(actor, "volunteer_role.manage")
        role = get_object_or_404(VolunteerRole.objects.select_for_update(), pk=role_id)
        before = {
            "name_en": role.name_en,
            "name_ur": role.name_ur,
            "sort_order": role.sort_order,
        }
        role.name_en, role.name_ur = name_en.strip(), name_ur.strip()
        role.sort_order = sort_order
        role.full_clean()
        role.save(update_fields=["name_en", "name_ur", "sort_order"])
        audit.record(
            actor,
            "volunteer_role.updated",
            entity=role,
            before=before,
            after={
                "name_en": role.name_en,
                "name_ur": role.name_ur,
                "sort_order": role.sort_order,
            },
        )
        return role


def deactivate_volunteer_role(actor, role_id):
    """Retain the role and its history while removing it from new assignments."""
    with transaction.atomic():
        require(actor, "volunteer_role.manage")
        role = get_object_or_404(VolunteerRole.objects.select_for_update(), pk=role_id)
        before = {"is_active": role.is_active}
        role.is_active = False
        role.save(update_fields=["is_active"])
        audit.record(
            actor,
            "volunteer_role.updated",
            entity=role,
            before=before,
            after={"is_active": False},
        )
        return role


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
                .filter(pk=team_id, branch_id=branch.pk, is_active=True)
                .first()
            )
            if team is None:
                raise ValidationError(
                    {
                        "team_id": _(
                            "Choose an active team from this application's branch."
                        )
                    }
                )
        role = (
            VolunteerRole.objects.select_for_update(no_key=True)
            .filter(pk=role_id, is_active=True)
            .first()
        )
        if role is None:
            raise ValidationError({"role_id": _("Choose an active volunteer role.")})
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
