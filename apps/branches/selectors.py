"""Read-only branch listings and scoped history for the register."""

from decimal import Decimal

from django.db.models import (
    Case,
    Count,
    DecimalField,
    IntegerField,
    OuterRef,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _

from apps.accounts.permissions import scope_queryset
from apps.audit.models import AuditLog
from apps.branches.models import Branch, BranchStatus
from apps.core import clock
from apps.finance.models import Collection
from apps.volunteers.models import Member, MemberStatus

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


def with_register_counts(user, queryset):
    """Add permission-gated counts to scoped branches without multiplying joins."""
    current = clock.now()
    member_branches = scope_queryset(
        user, "member.list", Branch.objects.all(), branch_field="pk"
    ).values("pk")
    money_branches = scope_queryset(
        user, "collection.list", Branch.objects.all(), branch_field="pk"
    ).values("pk")
    members = (
        Member.objects.filter(
            branch_id=OuterRef("pk"),
            status=MemberStatus.ACTIVE,
            created_at__lte=current,
        )
        .order_by()
        .values("branch_id")
        .annotate(total=Count("pk"))
    )
    # BR-071 / K4: all-time receipts with neither a transfer nor a void.
    unsent = (
        Collection.objects.filter(
            branch_id=OuterRef("pk"),
            transfer_id__isnull=True,
            voided_at__isnull=True,
            created_at__lte=current,
        )
        .order_by()
        .values("branch_id")
        .annotate(receipts=Count("pk"), amount=Sum("amount"))
    )
    # CASE keeps a denied count null; COALESCE gives an allowed empty branch zero.
    # Separate grouped subqueries avoid a members × collections join.
    return queryset.annotate(
        member_count=Case(
            When(
                pk__in=member_branches,
                then=Coalesce(Subquery(members.values("total")), Value(0)),
            ),
            default=Value(None),
            output_field=IntegerField(),
        ),
        unsent_count=Case(
            When(
                pk__in=money_branches,
                then=Coalesce(Subquery(unsent.values("receipts")), Value(0)),
            ),
            default=Value(None),
            output_field=IntegerField(),
        ),
        unsent_amount=Case(
            When(
                pk__in=money_branches,
                then=Coalesce(
                    Subquery(unsent.values("amount")), Value(Decimal("0.00"))
                ),
            ),
            default=Value(None),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
    )


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
