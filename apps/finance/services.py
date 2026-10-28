"""Validate offline money records and audit each write in its transaction."""

import re
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

from apps import audit
from apps.accounts.permissions import require, scope_queryset
from apps.branches.models import Branch, BranchStatus
from apps.core import clock, ids, rules
from apps.core.exceptions import InvalidTransition
from apps.finance.models import Collection, CollectionMethod, Transfer
from apps.volunteers.models import Member

EDITABLE_FIELDS = (
    "collection_date",
    "amount",
    "method",
    "receipt_no",
    "collected_by_member_id",
    "source_note",
)


def create_transfer(
    actor, branch, collection_ids, transfer_date, bank_reference, note=""
):
    """Send whole unsent entries once; locking and approval are independent. BR-069."""
    with transaction.atomic():
        require(actor, "transfer.create")
        branch = get_object_or_404(
            scope_queryset(
                actor,
                "transfer.create",
                Branch.objects.select_for_update(no_key=True),
                branch_field="pk",
            ),
            pk=branch.pk,
        )
        require(actor, "transfer.create", branch)
        selected_ids = sorted(set(collection_ids))
        if not selected_ids:
            raise ValidationError({"collections": _("Choose at least one collection.")})
        items = list(
            Collection.objects.select_for_update(no_key=True)
            .filter(branch=branch, pk__in=selected_ids)
            .order_by("pk")
        )
        if len(items) != len(selected_ids):
            raise ValidationError(
                {"collections": _("Choose only collections from this branch.")}
            )
        if any(
            item.voided_at is not None or item.transfer_id is not None for item in items
        ):
            raise InvalidTransition(
                _("A selected collection is voided or already sent.")
            )
        if (
            not max(item.collection_date for item in items)
            <= transfer_date
            <= clock.today()
        ):
            raise ValidationError(
                {
                    "transfer_date": _(
                        "Choose a transfer date between the latest "
                        "collection date and today."
                    )
                }
            )
        bank_reference = bank_reference.strip()
        if (
            not rules.get("transfer_bank_reference_min_length")
            <= len(bank_reference)
            <= rules.get("transfer_bank_reference_max_length")
        ):
            raise ValidationError(
                {"bank_reference": _("Use 3–50 characters for the bank reference.")}
            )
        number = ids.next_value(f"transfer:{branch.code}")
        transfer = Transfer(
            reference=f"TRF-{branch.code}-{number:04d}",
            branch=branch,
            transfer_date=transfer_date,
            bank_reference=bank_reference,
            total_amount=sum((item.amount for item in items), Decimal("0.00")),
            note=note.strip(),
            created_by=actor,
            created_at=clock.now(),
        )
        transfer.full_clean()
        transfer.save(force_insert=True)
        audit.record(
            actor,
            "transfer.created",
            entity=transfer,
            branch_id=branch.pk,
            after={
                "transfer_date": transfer.transfer_date,
                "bank_reference": transfer.bank_reference,
                "total_amount": transfer.total_amount,
                "collection_ids": selected_ids,
                "note": transfer.note,
            },
        )
        for item in items:
            item.transfer, item.updated_at = transfer, clock.now()
            # Deliberately bypass the edit guard: locked-but-unsent entries can be sent.
            item.save(update_fields=["transfer", "updated_at"])
            audit.record(
                actor,
                "collection.sent",
                entity=item,
                branch_id=branch.pk,
                before={"transfer_id": None},
                after={"transfer_id": transfer.pk},
            )
        return transfer


def assert_editable(collection):
    """The one edit/void state guard, shared with model saves. BR-064, BR-065."""
    if collection.voided_at is not None:
        raise InvalidTransition(_("This entry has been voided."))
    if collection.transfer_id is not None:
        raise InvalidTransition(_("This entry has already been sent."))
    lock_at = collection.lock_at
    if clock.now() >= lock_at:
        raise InvalidTransition(
            _("This entry locked on %(when)s (PKT).")
            % {"when": date_format(lock_at.astimezone(clock.KARACHI), "d M Y, H:i")}
        )
    if week_is_closed(collection.branch, collection.collection_date):
        raise InvalidTransition(_("This collection week is closed."))


def _change_collection(actor, collection, action, data=None, reason=""):
    """Commit a refused-attempt audit before raising its state conflict."""
    permission = "collection.update" if action == "update" else "collection.void"
    denied = None
    with transaction.atomic():
        require(actor, permission)
        scoped = scope_queryset(actor, permission, Collection.objects.all())
        item = get_object_or_404(scoped, pk=collection.pk)
        Branch.objects.select_for_update(no_key=True).get(pk=item.branch_id)
        item = get_object_or_404(scoped.select_for_update(no_key=True), pk=item.pk)
        try:
            assert_editable(item)
            if action == "update":
                values = validated_values(item.branch, data)
                if (
                    Collection.objects.filter(
                        branch_id=item.branch_id, receipt_no=values["receipt_no"]
                    )
                    .exclude(pk=item.pk)
                    .exists()
                ):
                    raise ValidationError(
                        {
                            "receipt_no": _(
                                "This receipt number already exists in this branch."
                            )
                        }
                    )
                before = {field: getattr(item, field) for field in EDITABLE_FIELDS}
                for field, value in values.items():
                    setattr(item, field, value)
                item.updated_at = clock.now()
                item.full_clean()
                item.save(
                    update_fields=[
                        "collection_date",
                        "amount",
                        "method",
                        "receipt_no",
                        "collected_by_member",
                        "source_note",
                        "updated_at",
                    ]
                )
                audit.record(
                    actor,
                    "collection.updated",
                    entity=item,
                    branch_id=item.branch_id,
                    before=before,
                    after={field: getattr(item, field) for field in EDITABLE_FIELDS},
                )
            else:
                reason = reason.strip()
                if (
                    not rules.get("collection_void_reason_min_length")
                    <= len(reason)
                    <= rules.get("collection_void_reason_max_length")
                ):
                    raise ValidationError(
                        {
                            "reason": _(
                                "Give a void reason between %(minimum)s "
                                "and %(maximum)s characters."
                            )
                            % {
                                "minimum": rules.get(
                                    "collection_void_reason_min_length"
                                ),
                                "maximum": rules.get(
                                    "collection_void_reason_max_length"
                                ),
                            }
                        }
                    )
                item.voided_at, item.voided_by, item.void_reason = (
                    clock.now(),
                    actor,
                    reason,
                )
                item.updated_at = clock.now()
                item.full_clean()
                item.save(
                    update_fields=[
                        "voided_at",
                        "voided_by",
                        "void_reason",
                        "updated_at",
                    ]
                )
                audit.record(
                    actor,
                    "collection.voided",
                    entity=item,
                    branch_id=item.branch_id,
                    before={"voided_at": None},
                    after={
                        "voided_at": item.voided_at,
                        "voided_by_id": actor.pk,
                        "void_reason": reason,
                    },
                )
        except InvalidTransition as error:
            denied = error
            audit.record(
                actor,
                "collection.edit_denied",
                entity=item,
                branch_id=item.branch_id,
                metadata={"action": action, "reason": str(error)},
            )
    if denied is not None:
        raise denied
    return item


def update_collection(actor, collection, data):
    """Update mutable collection fields under the shared state guard."""
    return _change_collection(actor, collection, "update", data=data)


def void_collection(actor, collection, reason):
    """Retain a receipt while excluding it from every live total. BR-068."""
    return _change_collection(actor, collection, "void", reason=reason)


def week_is_closed(branch, collection_date):
    """Submitted and approved report weeks block finance edits. BR-065."""
    from apps.finance.report_selectors import week_is_closed as report_week_is_closed

    return report_week_is_closed(branch, collection_date)


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
