from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils.translation import gettext_lazy as _

from apps.accounts.permissions import can, scope_queryset
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.core import clock, rules
from apps.finance.models import Collection, Transfer


def collections():
    return Collection.objects.select_related(
        "branch", "collected_by_member", "created_by", "voided_by", "transfer"
    ).order_by("-collection_date", "-pk")


def transfers():
    return Transfer.objects.select_related("branch", "created_by").order_by(
        "-transfer_date", "-pk"
    )


def unsent(user):
    """BR-071: neither locking nor report approval changes whether money is unsent."""
    return scope_queryset(user, "transfer.create", collections()).filter(
        transfer__isnull=True, voided_at__isnull=True
    )


def selection_has_conflict(user, branch, ids):
    return (
        scope_queryset(user, "collection.view", Collection.objects.all())
        .filter(branch=branch, pk__in=ids)
        .filter(Q(transfer__isnull=False) | Q(voided_at__isnull=False))
        .exists()
    )


def managed_branches(user, action="collection.create"):
    return scope_queryset(
        user, action, Branch.objects.order_by("code"), branch_field="pk"
    )


def search_collections(user, params):
    queryset = scope_queryset(user, "collection.list", collections())
    if params.get("date_from"):
        queryset = queryset.filter(collection_date__gte=params["date_from"])
    if params.get("date_to"):
        queryset = queryset.filter(collection_date__lte=params["date_to"])
    if params.get("method"):
        queryset = queryset.filter(method=params["method"])
    state = params.get("state")
    if state == "VOIDED":
        queryset = queryset.filter(voided_at__isnull=False)
    elif state == "SENT":
        queryset = queryset.filter(voided_at__isnull=True, transfer__isnull=False)
    elif state == "UNSENT":
        queryset = queryset.filter(voided_at__isnull=True, transfer__isnull=True)
    elif state in {"OPEN", "LOCKED"}:
        queryset = queryset.filter(voided_at__isnull=True, transfer__isnull=True)
        cutoff = clock.now() - timedelta(days=rules.get("collection_lock_days"))
        queryset = (
            queryset.filter(created_at__gt=cutoff)
            if state == "OPEN"
            else queryset.filter(created_at__lte=cutoff)
        )
    return queryset


def totals(queryset):
    return queryset.filter(voided_at__isnull=True).aggregate(
        total=Sum("amount", default=Decimal("0.00")), count=Count("pk")
    )


def history(user, collection):
    if not can(user, "audit.entity_history", collection):
        return []
    actions = {
        "collection.created": _("Collection created"),
        "collection.updated": _("Collection updated"),
        "collection.voided": _("Collection voided"),
        "collection.edit_denied": _("Collection edit refused"),
        "collection.sent": _("Collection sent"),
    }
    return [
        {
            "event": event,
            "action_label": actions.get(event.action, event.action),
            "changes": [
                {
                    "field": key,
                    "before": event.before.get(key),
                    "after": event.after.get(key),
                }
                for key in sorted(event.before.keys() | event.after.keys())
            ],
        }
        for event in AuditLog.objects.filter(
            entity_type="collection", entity_id=collection.pk
        ).order_by("-occurred_at", "-pk")
    ]
