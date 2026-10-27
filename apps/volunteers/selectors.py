import re

from django.db.models import Q
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from apps.accounts.permissions import can, scope_queryset
from apps.audit.models import AuditLog
from apps.branches.models import Branch, BranchStatus
from apps.volunteers.models import (
    Application,
    ApplicationStatus,
    Member,
    MemberStatus,
    Team,
    VolunteerRole,
)


def teams():
    return Team.objects.select_related("branch").order_by("branch__code", "name", "pk")


def team_management_branches(user):
    return scope_queryset(
        user, "team.manage", Branch.objects.order_by("code"), branch_field="pk"
    )


def volunteer_roles():
    return VolunteerRole.objects.order_by("sort_order", "code")


def applications():
    """Load the branch and decision labels used by the review pages."""
    return Application.objects.select_related(
        "preferred_branch", "decided_by", "member"
    ).order_by("-created_at", "-pk")


def members():
    return Member.objects.select_related("branch", "team", "volunteer_role")


def member_history(user, member):
    """Build rows for the shared, permission-checked history partial."""
    if not can(user, "audit.entity_history", member):
        return []
    labels = {
        "status": _("Status"),
        "left_on": _("Left on"),
        "team_id": _("Team"),
        "volunteer_role_id": _("Volunteer role"),
        "phone": _("Mobile number"),
        "notes": _("Notes"),
        "member_id": _("Member ID"),
        "branch_id": _("Branch"),
    }
    actions = {
        "member.created": _("Member created"),
        "member.updated": _("Member updated"),
        "member.status_changed": _("Member status changed"),
        "member.reinstated": _("Member reinstated"),
    }
    return [
        {
            "event": event,
            "action_label": actions.get(event.action, event.action),
            "changes": [
                {
                    "field": labels.get(field, field),
                    "before": event.before.get(field),
                    "after": event.after.get(field),
                }
                for field in sorted(event.before.keys() | event.after.keys())
            ],
        }
        for event in AuditLog.objects.filter(
            entity_type="member", entity_id=member.pk
        ).order_by("-occurred_at", "-pk")
    ]


def member_branches(user):
    return scope_queryset(
        user, "member.list", Branch.objects.order_by("code"), branch_field="pk"
    )


def member_teams(user):
    return scope_queryset(user, "member.list", teams())


def search_members(user, params):
    """Apply validated GET filters with AND, inside the caller's scope. BR-059."""
    queryset = scope_queryset(user, "member.list", members())
    query = params.get("q", "").strip()
    if query:
        matches = (
            Q(full_name__icontains=query)
            | Q(email__icontains=query)
            | Q(member_id__icontains=query)
        )
        # Only phone-shaped input adds a digits match; IDs containing digits do not.
        if re.fullmatch(r"[+0-9\s()\-]+", query):
            digits = re.sub(r"[^0-9]", "", query)
            if digits.startswith("03"):
                digits = digits[1:]
            if digits:
                matches |= Q(phone__contains=digits)
        queryset = queryset.filter(matches)
    for parameter, field in (
        ("branch", "branch_id"),
        ("team", "team_id"),
        ("role", "volunteer_role_id"),
    ):
        if params.get(parameter):
            queryset = queryset.filter(**{field: params[parameter]})
    status = params.get("status", MemberStatus.ACTIVE)
    if status:
        queryset = queryset.filter(status=status)
    if params.get("joined_from"):
        queryset = queryset.filter(joined_on__gte=params["joined_from"])
    if params.get("joined_to"):
        queryset = queryset.filter(joined_on__lte=params["joined_to"])
    orderings = {
        "name": (Lower("full_name").asc(), "pk"),
        "-name": (Lower("full_name").desc(), "pk"),
        "joined": ("joined_on", "pk"),
        "-joined": ("-joined_on", "-pk"),
    }
    return queryset.order_by(*orderings.get(params.get("sort"), ("-created_at", "-pk")))


def review_branches(user):
    """Include historical branches, but only inside the caller's scope."""
    return scope_queryset(user, "branch.list", Branch.objects.order_by("code"))


def duplicate_records(user, application):
    """Never load or expose a matched record outside the caller's view scope."""
    matched_application = (
        scope_queryset(user, "application.view", Application.objects.all())
        .filter(pk=application.duplicate_of_application_id)
        .first()
    )
    matched_member = (
        scope_queryset(user, "member.view", Member.objects.all())
        .filter(pk=application.duplicate_of_member_id)
        .first()
    )
    return {
        "application": matched_application,
        "member": matched_member,
        "hidden": bool(
            (application.duplicate_of_application_id and matched_application is None)
            or (application.duplicate_of_member_id and matched_member is None)
        ),
    }


def application_history(user, application):
    """Provide permission-checked rows for the shared entity history partial."""
    if not can(user, "audit.entity_history", application):
        return []
    labels = {
        "reference": _("Reference"),
        "preferred_branch_id": _("Preferred branch"),
        "status": _("Status"),
        "member_id": _("Member"),
        "decision_note": _("Decision note"),
    }
    actions = {
        "application.submitted": _("Application submitted"),
        "application.accepted": _("Application accepted"),
        "application.declined": _("Application declined"),
        "application.reassigned": _("Application reassigned"),
    }
    events = AuditLog.objects.filter(
        entity_type="application", entity_id=application.pk
    ).order_by("-occurred_at", "-pk")
    return [
        {
            "event": event,
            "action_label": actions.get(event.action, event.action),
            "changes": [
                {
                    "field": labels.get(field, field),
                    "before": event.before.get(field),
                    "after": value,
                }
                for field, value in event.after.items()
            ],
        }
        for event in events
    ]


def accepting_branches():
    return (
        Branch.objects.filter(status__in=[BranchStatus.ACTIVE, BranchStatus.FORMING])
        .select_related("city")
        .order_by("city__code", "name_en", "pk")
    )


def duplicate_application(email, phone):
    return (
        Application.objects.filter(status=ApplicationStatus.PENDING)
        .filter(Q(email__iexact=email) | Q(phone=phone))
        .order_by("pk")
        .first()
    )


def duplicate_member(email, phone):
    return (
        Member.objects.exclude(status=MemberStatus.LEFT)
        .filter(Q(email__iexact=email) | Q(phone=phone))
        .order_by("pk")
        .first()
    )
