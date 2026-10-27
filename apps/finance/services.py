"""Validate offline money records and audit each write in its transaction."""

import re
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from apps import audit
from apps.accounts.permissions import require, scope_queryset
from apps.branches.models import Branch, BranchStatus
from apps.core import clock, ids, rules
from apps.core.exceptions import InvalidTransition
from apps.finance.models import Collection, CollectionMethod
from apps.volunteers.models import Member

EDITABLE_FIELDS = (
    "collection_date",
    "amount",
    "method",
    "receipt_no",
    "collected_by_member_id",
    "source_note",
)


def week_is_closed(branch, collection_date):
    """P7 will check submitted, resubmitted and locked weekly reports here. BR-065."""
    return False


def validated_values(branch, data):
    """Keep BR-060–063 and BR-065 authoritative for direct service callers too."""
    try:
        if isinstance(data["amount"], (float, bool)):
            raise InvalidOperation
        amount = Decimal(data["amount"])
        if (
            not amount.is_finite()
            or not Decimal("0") < amount <= rules.get("max_collection")
            or amount != amount.quantize(Decimal("0.01"))
        ):
            raise InvalidOperation
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(
            {
                "amount": _(
                    "Enter a positive amount with at most two decimal places "
                    "within the allowed maximum."
                )
            }
        ) from None
    today = clock.today()
    collection_date = data["collection_date"]
    if (
        not today - timedelta(days=rules.get("collection_lock_days"))
        <= collection_date
        <= today
    ):
        raise ValidationError(
            {
                "collection_date": _(
                    "Choose a date within the allowed collection window."
                )
            }
        )
    if data["method"] not in CollectionMethod.values:
        raise ValidationError({"method": _("Choose an offline collection method.")})
    receipt = data["receipt_no"].strip()
    if not re.fullmatch(r"[A-Za-z0-9\-/]{1,30}", receipt):
        raise ValidationError(
            {
                "receipt_no": _(
                    "Use 1–30 letters, numbers, slashes or dashes for the receipt."
                )
            }
        )
    if week_is_closed(branch, collection_date):
        raise InvalidTransition(_("This collection week is closed."))
    member = data.get("collected_by")
    if member is not None:
        member_id = member.pk if isinstance(member, Member) else member
        member = Member.objects.filter(pk=member_id, branch_id=branch.pk).first()
        if member is None:
            raise ValidationError(
                {"collected_by": _("Choose a member from this branch.")}
            )
    note = data.get("source_note", "").strip()
    if len(note) > 200:
        raise ValidationError(
            {"source_note": _("Use at most 200 characters for the source note.")}
        )
    return {
        "collection_date": collection_date,
        "amount": amount,
        "method": data["method"],
        "receipt_no": receipt,
        "collected_by_member": member,
        "source_note": note,
    }


def create_collection(actor, branch, data):
    """Reserve a branch reference and insert an audited offline entry. BR-060–066."""
    with transaction.atomic():
        require(actor, "collection.create")
        branch = get_object_or_404(
            scope_queryset(
                actor,
                "collection.create",
                Branch.objects.select_for_update(no_key=True),
                branch_field="pk",
            ),
            pk=branch.pk,
        )
        require(actor, "collection.create", branch)
        if branch.status != BranchStatus.ACTIVE:
            raise InvalidTransition(
                _("Collections can only be entered for an active branch.")
            )
        values = validated_values(branch, data)
        if Collection.objects.filter(
            branch=branch, receipt_no=values["receipt_no"]
        ).exists():
            raise ValidationError(
                {"receipt_no": _("This receipt number already exists in this branch.")}
            )
        number = ids.next_value(f"collection:{branch.code}")
        collection = Collection(
            branch=branch,
            reference=f"COL-{branch.code}-{number:05d}",
            created_by=actor,
            created_at=clock.now(),
            updated_at=clock.now(),
            **values,
        )
        collection.full_clean()
        collection.save(force_insert=True)
        audit.record(
            actor,
            "collection.created",
            entity=collection,
            branch_id=branch.pk,
            after={field: getattr(collection, field) for field in EDITABLE_FIELDS},
        )
        return collection
