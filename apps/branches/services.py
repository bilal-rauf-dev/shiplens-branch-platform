"""Branch register writes set protected fields and audit within one transaction."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps import audit
from apps.accounts.permissions import require, scope_queryset
from apps.branches.models import Branch, BranchStatus, City
from apps.core import clock, ids, rules

EDITABLE_FIELDS = ("name_en", "name_ur", "address_en", "address_ur", "phone", "email")


class InvalidTransition(Exception):
    """The requested state change is unavailable or blocked by business records."""


def close_blockers(branch):
    """Return the reasons a branch cannot close. BR-011."""
    # P6 adds unsent collections; P7 adds open reports to this guard.
    return []


def _require_reason(branch, reason):
    """Require a useful explanation for pausing or closing a branch."""
    minimum = rules.get("branch_reason_min_length")
    maximum = rules.get("branch_reason_max_length")
    if not minimum <= len(reason) <= maximum:
        raise ValidationError(
            _("Give a reason between %(minimum)s and %(maximum)s characters.")
            % {"minimum": minimum, "maximum": maximum}
        )


def _guard_close(branch, reason):
    _require_reason(branch, reason)
    blockers = close_blockers(branch)
    if blockers:
        raise InvalidTransition(
            _("This branch cannot be closed: %(blockers)s")
            % {"blockers": "; ".join(blockers)}
        )


# BR-010: only these state/action pairs are allowed. CLOSED is terminal.
BRANCH_TRANSITIONS = {
    (BranchStatus.FORMING, "activate"): (BranchStatus.ACTIVE, None),
    (BranchStatus.ACTIVE, "pause"): (BranchStatus.PAUSED, _require_reason),
    (BranchStatus.PAUSED, "resume"): (BranchStatus.ACTIVE, None),
    (BranchStatus.FORMING, "close"): (BranchStatus.CLOSED, _guard_close),
    (BranchStatus.ACTIVE, "close"): (BranchStatus.CLOSED, _guard_close),
    (BranchStatus.PAUSED, "close"): (BranchStatus.CLOSED, _guard_close),
}

TRANSITION_EVENTS = {
    "activate": "branch.activated",
    "pause": "branch.paused",
    "resume": "branch.resumed",
    "close": "branch.closed",
}


def _lifecycle_fields(branch):
    return {
        "status": branch.status,
        "status_reason": branch.status_reason,
        "opened_on": branch.opened_on,
        "closed_on": branch.closed_on,
    }


def transition(actor, branch, action, reason=""):
    """Lock, validate and audit a branch lifecycle change. BR-010, BR-011."""
    with transaction.atomic():
        require(actor, "branch.transition", branch)
        branch = scope_queryset(
            actor, "branch.transition", Branch.objects.select_for_update(no_key=True)
        ).get(pk=branch.pk)
        change = BRANCH_TRANSITIONS.get((branch.status, action))
        if change is None:
            raise InvalidTransition(
                _("This action is not allowed in the branch's current state.")
            )
        target_status, guard = change
        reason = reason.strip()
        if guard is not None:
            guard(branch, reason)
        before = _lifecycle_fields(branch)
        branch.status = target_status
        branch.status_reason = reason if action in {"pause", "close"} else ""
        if action == "activate" and branch.opened_on is None:
            branch.opened_on = clock.today()
        if action == "close":
            branch.closed_on = clock.today()
        branch.updated_by = actor
        branch.updated_at = clock.now()
        branch.full_clean()
        branch.save(
            update_fields=[
                "status",
                "status_reason",
                "opened_on",
                "closed_on",
                "updated_by",
                "updated_at",
            ]
        )
        audit.record(
            actor,
            TRANSITION_EVENTS[action],
            entity=branch,
            branch_id=branch.pk,
            before=before,
            after=_lifecycle_fields(branch),
        )
        return branch


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
