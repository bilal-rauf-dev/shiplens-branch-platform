from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import Role, UserBranchAssignment
from apps.audit.models import AuditLog
from apps.branches.models import BranchStatus
from apps.core import clock as business_clock
from apps.core.exceptions import InvalidTransition
from apps.core.models import IdSequence
from apps.finance import services
from apps.finance.forms import CollectionForm
from apps.finance.models import Collection
from apps.volunteers.models import Member, VolunteerRole

pytestmark = pytest.mark.django_db


def test_t_col_create(bl, branch, collection_data):
    form = CollectionForm(collection_data, branch=branch)
    assert form.is_valid(), form.errors
    item = services.create_collection(bl, branch, form.cleaned_data)
    assert item.reference == "COL-BR-KHI-01-00001" and item.created_by == bl
    assert item.amount == Decimal("100.00") and item.created_at == business_clock.now()
    assert item.transfer_id is None and item.voided_at is None
    assert AuditLog.objects.get(action="collection.created").after["amount"] == "100.00"
    assert str(item) == item.reference


@pytest.mark.parametrize(
    "amount", ["0", "-1", "0.001", "10000000.01", "NaN", "Infinity"]
)
def test_t_col_amount_rejected(bl, branch, collection_data, amount):
    with pytest.raises(ValidationError):
        services.create_collection(
            bl, branch, {**collection_data, "amount": Decimal(amount)}
        )
    assert not Collection.objects.exists() and not IdSequence.objects.exists()
    assert not CollectionForm(
        {**collection_data, "amount": amount}, branch=branch
    ).is_valid()


@pytest.mark.parametrize("amount", ["0.01", "10000000.00"])
def test_t_col_amount_boundaries(bl, branch, collection_data, amount):
    assert services.create_collection(
        bl, branch, {**collection_data, "amount": Decimal(amount)}
    ).amount == Decimal(amount)


@pytest.mark.parametrize("method", ["CARD", "GATEWAY", "BANK", ""])
def test_t_col_method(bl, branch, collection_data, method):
    with pytest.raises(ValidationError):
        services.create_collection(bl, branch, {**collection_data, "method": method})


@pytest.mark.parametrize(
    "offset,valid", [(-7, True), (-8, False), (1, False), (0, True)]
)
def test_t_col_date_range_pkt(bl, branch, collection_data, clock, offset, valid):
    clock.move_to("2026-10-25T20:30:00Z")
    assert business_clock.today() == date(2026, 10, 26)
    data = {
        **collection_data,
        "collection_date": business_clock.today() + timedelta(days=offset),
    }
    if valid:
        assert (
            services.create_collection(bl, branch, data).collection_date
            == data["collection_date"]
        )
    else:
        with pytest.raises(ValidationError):
            services.create_collection(bl, branch, data)


def test_t_col_receipt_unique(bl, branch, collection_data, branch_factory):
    services.create_collection(bl, branch, collection_data)
    with pytest.raises(ValidationError):
        services.create_collection(bl, branch, collection_data)
    other = branch_factory(code="BR-LHE-01", status=BranchStatus.ACTIVE)
    UserBranchAssignment.objects.create(user=bl, branch=other, created_by=bl)
    assert services.create_collection(bl, other, collection_data).branch == other
    assert Collection.objects.count() == 2


@pytest.mark.parametrize(
    "status", [BranchStatus.FORMING, BranchStatus.PAUSED, BranchStatus.CLOSED]
)
def test_t_col_branch_active(bl, branch, collection_data, status):
    branch.status = status
    branch.save(update_fields=["status"])
    with pytest.raises(InvalidTransition):
        services.create_collection(bl, branch, collection_data)


def test_t_col_no_online(branch):
    model_fields = {field.name for field in Collection._meta.fields}
    form_fields = set(CollectionForm(branch=branch).fields)
    for prohibited in ("card", "iban", "gateway", "payment_token", "online_payment"):
        assert not any(prohibited in name for name in model_fields | form_fields)
    assert form_fields == {
        "collection_date",
        "amount",
        "method",
        "receipt_no",
        "collected_by",
        "source_note",
    }
    form = CollectionForm(branch=branch)
    assert form.fields["amount"].widget.attrs == {
        "step": "0.01",
        "min": "0.01",
        "max": "10000000.00",
    }
    assert form.fields["collection_date"].widget.attrs["min"] == "2026-10-18"
    assert form.fields["collection_date"].widget.attrs["max"] == "2026-10-25"


@pytest.mark.parametrize(
    "changes",
    [
        {"amount": Decimal("0")},
        {"method": "CARD"},
        {"entry_type": "ADJUSTMENT"},
        {"void_reason": "partial"},
    ],
)
def test_collection_database_checks(collection, changes):
    with pytest.raises(IntegrityError), transaction.atomic():
        Collection.objects.filter(pk=collection.pk).update(**changes)


def test_collection_rollback_on_audit_failure(bl, branch, collection_data):
    with patch(
        "apps.finance.services.audit.record", side_effect=RuntimeError("unavailable")
    ):
        with pytest.raises(RuntimeError):
            services.create_collection(bl, branch, collection_data)
    assert not Collection.objects.exists() and not IdSequence.objects.exists()


def test_collection_wrong_role_and_week_hook(bl, branch, collection_data):
    bl.role = Role.FINANCE_REVIEWER
    with pytest.raises(PermissionDenied):
        services.create_collection(bl, branch, collection_data)
    bl.role = Role.BRANCH_LEAD
    with patch("apps.finance.services.week_is_closed", return_value=True):
        with pytest.raises(InvalidTransition):
            services.create_collection(bl, branch, collection_data)


def test_collected_by_must_be_same_branch(bl, branch, collection_data, branch_factory):
    other = branch_factory(code="BR-LHE-01")
    role = VolunteerRole.objects.get(code="VOLUNTEER")
    member = Member.objects.create(
        member_id="M-2026-00001",
        branch=other,
        volunteer_role=role,
        full_name="Other member",
        email="other@example.com",
        phone="+923001234567",
        joined_on=business_clock.today(),
        created_by=bl,
        updated_by=bl,
    )
    data = {**collection_data, "collected_by": member}
    with pytest.raises(ValidationError):
        services.create_collection(bl, branch, data)
    form = CollectionForm({**collection_data, "collected_by": member.pk}, branch=branch)
    assert not form.is_valid() and "collected_by" in form.errors
