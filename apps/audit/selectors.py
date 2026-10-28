"""Read-only audit queries and verification of the append-only chain."""

import json
from datetime import datetime, time

from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Role, User
from apps.accounts.permissions import can, scope_queryset
from apps.audit.models import AuditLog
from apps.audit.services import GENESIS_HASH, _hash
from apps.branches.models import Branch, City
from apps.core import clock
from apps.finance.models import Collection, Transfer, WeeklyReport
from apps.volunteers.models import Application, Member, Team, VolunteerRole


def events():
    return AuditLog.objects.order_by("-occurred_at", "-pk")


def action_choices():
    """Keep grouped choices in sync with actual recorded actions."""
    labels = {
        "auth": _("Authentication"),
        "member": _("Members"),
        "team": _("Teams"),
        "volunteer_role": _("Volunteer roles"),
        "branch": _("Branches"),
        "city": _("Cities"),
        "application": _("Applications"),
        "audit": _("Audit"),
        "user": _("Users"),
        "permission": _("Permissions"),
        "settings": _("System settings"),
        "assignment": _("Assignments"),
    }
    groups = {}
    for action in (
        AuditLog.objects.order_by("action").values_list("action", flat=True).distinct()
    ):
        prefix = action.split(".", 1)[0]
        groups.setdefault(prefix, []).append((action, action))
    return [
        ("", _("All actions")),
        *[(labels.get(prefix, prefix), choices) for prefix, choices in groups.items()],
    ]


def entity_types():
    return (
        AuditLog.objects.exclude(entity_type="")
        .order_by("entity_type")
        .values_list("entity_type", flat=True)
        .distinct()
    )


def search_events(user, params):
    """Filter timestamps directly with inclusive Karachi-day boundaries."""
    queryset = scope_queryset(user, "audit.list", events())
    if params.get("date_from"):
        queryset = queryset.filter(
            occurred_at__gte=datetime.combine(
                params["date_from"], time.min, tzinfo=clock.KARACHI
            )
        )
    if params.get("date_to"):
        queryset = queryset.filter(
            occurred_at__lte=datetime.combine(
                params["date_to"], time.max, tzinfo=clock.KARACHI
            )
        )
    if params.get("actor"):
        queryset = queryset.filter(actor_label__icontains=params["actor"])
    for parameter, field in (
        ("role", "actor_role"),
        ("action", "action"),
        ("entity_type", "entity_type"),
    ):
        if params.get(parameter):
            queryset = queryset.filter(**{field: params[parameter]})
    query = params.get("entity", "").strip()
    if query:
        matches = Q(entity_label__icontains=query)
        if query.isdecimal() and int(query).bit_length() <= 63:
            matches |= Q(entity_id=int(query))
        queryset = queryset.filter(matches)
    if params.get("branch"):
        queryset = queryset.filter(branch_id=params["branch"].pk)
    return queryset


ENTITY_ROUTES = {
    "weeklyreport": (WeeklyReport, "report.view", "report-detail"),
    "collection": (Collection, "collection.view", "collection-detail"),
    "transfer": (Transfer, "transfer.view", "transfer-detail"),
    "branch": (Branch, "branch.view", "branch-detail"),
    "member": (Member, "member.view", "member-detail"),
    "application": (Application, "application.view", "application-detail"),
    "user": (User, "user.view", "user-detail"),
    "city": (City, "city.manage", "city-edit"),
    "team": (Team, "team.manage", "team-edit"),
    "volunteerrole": (VolunteerRole, "volunteer_role.manage", "volunteer-role-edit"),
}


def viewer_rows(user, event_list):
    """Batch entity lookups and link only records the viewer may still access."""
    event_list = list(event_list)
    objects = {}
    for entity_type, (model, action, _route) in ENTITY_ROUTES.items():
        ids = {
            event.entity_id
            for event in event_list
            if event.entity_type == entity_type and event.entity_id is not None
        }
        if ids:
            objects[entity_type] = scope_queryset(
                user, action, model.objects.all()
            ).in_bulk(ids)
    branches = dict(
        Branch.objects.filter(
            pk__in={event.branch_id for event in event_list if event.branch_id}
        ).values_list("pk", "code")
    )
    rows = []
    for event in event_list:
        url = None
        target = objects.get(event.entity_type, {}).get(event.entity_id)
        if target is not None:
            _model, action, route = ENTITY_ROUTES[event.entity_type]
            if can(user, action, target):
                url = reverse(route, kwargs={"pk": target.pk})
        fields = sorted(event.before.keys() | event.after.keys())
        summary = ", ".join(fields[:3]) + (" …" if len(fields) > 3 else "")
        rows.append(
            {
                "event": event,
                "entity_url": url,
                "branch_code": branches.get(event.branch_id, event.branch_id or "—"),
                "actor_role": dict(Role.choices).get(
                    event.actor_role, event.actor_role or _("System / anonymous")
                ),
                "summary": summary or _("No field changes"),
            }
        )
    return rows


def changed_fields(event):
    """Render structured values as escaped JSON, keeping false and null visible."""
    return [
        {
            "field": field,
            "before": json.dumps(
                event.before[field], ensure_ascii=False, sort_keys=True, indent=2
            )
            if field in event.before
            else "—",
            "after": json.dumps(
                event.after[field], ensure_ascii=False, sort_keys=True, indent=2
            )
            if field in event.after
            else "—",
        }
        for field in sorted(event.before.keys() | event.after.keys())
    ]


def verify_chain():
    """Verify one ordered database snapshot and identify its first invalid row."""
    previous_hash = GENESIS_HASH
    # One SELECT gives a consistent snapshot even while other transactions append.
    for event in AuditLog.objects.order_by("pk").iterator():
        if event.prev_hash != previous_hash or event.hash != _hash(event):
            return False, event.pk
        previous_hash = event.hash
    return True, None
