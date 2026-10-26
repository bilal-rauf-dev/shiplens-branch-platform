"""Read-only branch listings and scoped history for the register."""

from django.utils.translation import gettext_lazy as _

from apps.audit.models import AuditLog
from apps.branches.models import Branch, BranchStatus

FIELD_LABELS = {
    "code": _("Code"),
    "city_id": _("City"),
    "status": _("Status"),
    "status_reason": _("Status reason"),
    "opened_on": _("Opened on"),
    "closed_on": _("Closed on"),
    "name_en": _("English name"),
    "name_ur": _("Urdu name"),
    "address_en": _("English address"),
    "address_ur": _("Urdu address"),
    "phone": _("Phone"),
    "email": _("Email"),
}
ACTION_LABELS = {
    "branch.created": _("Branch created"),
    "branch.updated": _("Branch updated"),
    "branch.activated": _("Branch activated"),
    "branch.paused": _("Branch paused"),
    "branch.resumed": _("Branch resumed"),
    "branch.closed": _("Branch closed"),
}


def branches():
    """Order branches predictably for the staff register."""
    return Branch.objects.select_related("city").order_by("city__code", "name_en", "pk")


def public_branches():
    """Exclude Closed branches from future public directory pages. BR-013."""
    return branches().exclude(status=BranchStatus.CLOSED)


def branch_history(branch):
    """Return only the audit events attached to this branch."""
    events = AuditLog.objects.filter(
        entity_type="branch", entity_id=branch.pk
    ).order_by("-occurred_at", "-pk")
    return [
        {
            "event": event,
            "action_label": ACTION_LABELS.get(event.action, event.action),
            "changes": [
                {
                    "field": FIELD_LABELS.get(field, field),
                    "before": event.before.get(field),
                    "after": value,
                }
                for field, value in event.after.items()
            ],
        }
        for event in events
    ]
