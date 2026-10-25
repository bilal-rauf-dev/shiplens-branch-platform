from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import (
    DatabaseError,
    IntegrityError,
    connection,
    connections,
    transaction,
)
from django.db.models.deletion import RestrictedError

from apps.accounts.models import Role, User
from apps.audit.models import AuditLog
from apps.audit.selectors import verify_chain
from apps.branches.models import Branch, BranchStatus, City
from apps.branches.services import create_branch, update_branch
from apps.core import clock as business_clock
from apps.core.models import IdSequence

pytestmark = pytest.mark.django_db


def test_city_seed_data():
    assert set(City.objects.values_list("code", "name_en", "name_ur")) == {
        ("KHI", "Karachi", "کراچی"),
        ("LHE", "Lahore", "لاہور"),
        ("ISB", "Islamabad", "اسلام آباد"),
        ("RWP", "Rawalpindi", "راولپنڈی"),
        ("PEW", "Peshawar", "پشاور"),
        ("QTA", "Quetta", "کوئٹہ"),
        ("MUX", "Multan", "ملتان"),
        ("FSD", "Faisalabad", "فیصل آباد"),
        ("HYD", "Hyderabad", "حیدرآباد"),
        ("SKT", "Sialkot", "سیالکوٹ"),
    }


@pytest.fixture
def actor():
    return User.objects.create_user(
        email="branches@example.com", full_name="Branch Admin", role=Role.SUPER_ADMIN
    )


@pytest.fixture
def city():
    return City.objects.get_or_create(
        code="KHI", defaults={"name_en": "Karachi", "name_ur": "کراچی"}
    )[0]


def create(actor, city, **fields):
    return create_branch(
        actor,
        city=city,
        **{
            "name_en": "Central",
            "name_ur": "مرکزی",
            "address_en": "",
            "address_ur": "",
            "phone": "",
            "email": "",
            **fields,
        },
    )


def test_t_brn_code_format(actor, city, clock):
    first = create(actor, city)
    second = create(actor, city, name_en="Second")
    assert (first.code, second.code) == ("BR-KHI-01", "BR-KHI-02")
    IdSequence.objects.filter(pk="branch:KHI").update(last_value=99)
    hundred = create(actor, city, name_en="Hundred")
    assert hundred.code == "BR-KHI-100"
    assert first.status == BranchStatus.FORMING
    assert first.created_by == first.updated_by == actor
    assert first.created_at == first.updated_at == business_clock.now()
    assert first.opened_on is first.closed_on is None
    assert str(city) == "Karachi"
    sequence = IdSequence.objects.get(pk="branch:KHI")
    assert str(sequence) == "branch:KHI"
    assert sequence.updated_at == business_clock.now()
    entry = AuditLog.objects.get(action="branch.created", entity_id=first.pk)
    assert entry.after["code"] == first.code
    assert entry.branch_id == first.pk
    assert verify_chain() == (True, None)


def test_t_brn_code_immutable(actor, city):
    branch = create(actor, city)
    with pytest.raises(DatabaseError, match="immutable"), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE branches SET code = %s WHERE id = %s", ["BR-KHI-99", branch.pk]
            )
    branch.refresh_from_db()
    assert branch.code == "BR-KHI-01"
    # Updating the row while retaining its code remains valid.
    Branch.objects.filter(pk=branch.pk).update(code=branch.code)


def test_t_brn_name_unique(actor, city):
    create(actor, city)
    with pytest.raises(ValidationError):
        create(actor, city, name_en="CENTRAL")
    with pytest.raises(IntegrityError), transaction.atomic():
        Branch.objects.create(
            code="BR-KHI-88", city=city, name_en="central", name_ur="مرکزی"
        )
    lahore, _ = City.objects.get_or_create(
        code="LHE", defaults={"name_en": "Lahore", "name_ur": "لاہور"}
    )
    assert create(actor, lahore).code == "BR-LHE-01"
    assert create(actor, city, name_en="Second").code == "BR-KHI-02"
    with pytest.raises(RestrictedError):
        city.delete()


@pytest.mark.parametrize("code", ["khi", "KH", "KH12", "K1I", "KHI\n"])
def test_t_city_code(code):
    with pytest.raises(ValidationError):
        City(code=code, name_en="Test", name_ur="شہر").full_clean()
    with pytest.raises(DatabaseError), transaction.atomic():
        City.objects.create(code=code, name_en="Test", name_ur="شہر")


def test_update_branch_audited(actor, city, clock):
    branch = create(actor, city)
    clock.shift(60)
    changed = update_branch(
        actor, branch, name_en="Renamed", email=" OFFICE@EXAMPLE.COM "
    )
    assert changed.code == branch.code and changed.city == city
    assert changed.status == BranchStatus.FORMING
    assert changed.email == "office@example.com"
    assert changed.updated_at == business_clock.now() > changed.created_at
    assert changed.updated_by == actor
    entry = AuditLog.objects.get(action="branch.updated")
    assert entry.before["name_en"] == "Central"
    assert entry.after["name_en"] == "Renamed"


@pytest.mark.parametrize("field", ["code", "status", "city", "created_by", "opened_on"])
def test_update_rejects_protected_fields(actor, city, field):
    branch = create(actor, city)
    with pytest.raises(ValidationError):
        update_branch(actor, branch, **{field: "changed"})
    assert not AuditLog.objects.filter(action="branch.updated").exists()


def test_invalid_updates_and_contacts(actor, city):
    branch = create(actor, city)
    for fields in ({}, {"phone": "021-123"}, {"email": "invalid"}, {"name_ur": ""}):
        with pytest.raises(ValidationError):
            update_branch(actor, branch, **fields)
    with pytest.raises(IntegrityError), transaction.atomic():
        Branch.objects.filter(pk=branch.pk).update(
            opened_on=date(2026, 10, 25), closed_on=date(2026, 10, 24)
        )
    assert not AuditLog.objects.filter(action="branch.updated").exists()


@pytest.mark.parametrize(
    "role", [Role.BRANCH_LEAD, Role.HR_LEAD, Role.FINANCE_REVIEWER, Role.CONTENT_EDITOR]
)
def test_services_require_permission(actor, city, role):
    branch = create(actor, city)
    other = User.objects.create_user(
        email="other@example.com", full_name="Other", role=role
    )
    with pytest.raises(PermissionDenied):
        create(other, city, name_en="Denied")
    with pytest.raises(PermissionDenied):
        update_branch(other, branch, name_en="Denied")
    assert Branch.objects.count() == 1
    assert AuditLog.objects.count() == 1


def test_failed_audit_rolls_back_branch_and_counter(actor, city):
    with patch(
        "apps.branches.services.audit.record",
        side_effect=RuntimeError("audit unavailable"),
    ):
        with pytest.raises(RuntimeError):
            create(actor, city)
    assert not Branch.objects.exists()
    assert not IdSequence.objects.exists()
    branch = create(actor, city)
    with patch(
        "apps.branches.services.audit.record",
        side_effect=RuntimeError("audit unavailable"),
    ):
        with pytest.raises(RuntimeError):
            update_branch(actor, branch, name_en="Rollback")
    branch.refresh_from_db()
    assert branch.name_en == "Central"


@pytest.mark.django_db(transaction=True)
def test_t_brn_code_race(actor, city):
    barrier = Barrier(10)

    def worker(index):
        try:
            barrier.wait(timeout=20)
            return create(actor, city, name_en=f"Concurrent {index}").code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=10) as pool:
        codes = list(pool.map(worker, range(10)))
    assert sorted(codes) == [f"BR-KHI-{number:02d}" for number in range(1, 11)]
    assert Branch.objects.count() == AuditLog.objects.count() == 10
    assert IdSequence.objects.get(pk="branch:KHI").last_value == 10
    assert verify_chain() == (True, None)
