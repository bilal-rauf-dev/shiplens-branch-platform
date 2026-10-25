"""Branch register writes set protected fields and audit within one transaction."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps import audit
from apps.accounts.permissions import require, scope_queryset
from apps.branches.models import Branch, BranchStatus, City
from apps.core import clock, ids

EDITABLE_FIELDS = ("name_en", "name_ur", "address_en", "address_ur", "phone", "email")


def _fields(branch):
    return {name: getattr(branch, name) for name in EDITABLE_FIELDS}


def create_branch(
    actor, *, city, name_en, name_ur, address_en, address_ur, phone, email
):
    """Generate a per-city code and create a Forming branch. BR-001, BR-012."""
    with transaction.atomic():
        require(actor, "branch.create")
        city = City.objects.get(pk=city.pk)
        number = ids.next_value(f"branch:{city.code}")
        branch = Branch(
            code=f"BR-{city.code}-{number:02d}",
            city=city,
            name_en=name_en,
            name_ur=name_ur,
            address_en=address_en,
            address_ur=address_ur,
            phone=phone,
            email=email.strip().lower(),
            status=BranchStatus.FORMING,
            created_by=actor,
            updated_by=actor,
            created_at=clock.now(),
            updated_at=clock.now(),
        )
        branch.full_clean()
        branch.save(force_insert=True)
        audit.record(
            actor,
            "branch.created",
            entity=branch,
            branch_id=branch.pk,
            after={
                "code": branch.code,
                "city_id": city.pk,
                "status": branch.status,
                **_fields(branch),
            },
        )
        return branch


def update_branch(actor, branch, **fields):
    """Edit name/address/contact only, preserving code, city and status. BR-002."""
    with transaction.atomic():
        require(actor, "branch.update", branch)
        if not fields or fields.keys() - set(EDITABLE_FIELDS):
            raise ValidationError(
                _("Only branch name, address and contact fields may be edited.")
            )
        branch = scope_queryset(
            actor, "branch.update", Branch.objects.select_for_update(no_key=True)
        ).get(pk=branch.pk)
        before = _fields(branch)
        for name, value in fields.items():
            if name == "email":
                value = value.strip().lower()
            setattr(branch, name, value)
        branch.updated_by = actor
        branch.updated_at = clock.now()
        branch.full_clean()
        branch.save(update_fields=[*fields, "updated_by", "updated_at"])
        audit.record(
            actor,
            "branch.updated",
            entity=branch,
            branch_id=branch.pk,
            before=before,
            after=_fields(branch),
        )
        return branch
