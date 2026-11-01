"""Register totals match the seed and respect each underlying list permission."""

import re
from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.accounts.permissions import GLOBAL, PERMISSIONS, scope_queryset
from apps.branches import selectors
from apps.branches.models import Branch, BranchStatus
from apps.dashboard import kpis
from apps.finance.models import Collection
from apps.volunteers.models import Member, MemberStatus, VolunteerRole
from tests.dashboard.conftest import AS_OF, sample_data  # noqa: F401

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("sample_data")]


@pytest.fixture(autouse=True)
def register_clock(clock):
    clock.move_to(AS_OF)


def register(user):
    return selectors.with_register_counts(
        user, scope_queryset(user, "branch.list", selectors.branches())
    )


def test_t_brn_register_seed_counts():
    user = User.objects.get(role=Role.SUPER_ADMIN)
    expected = {
        "BR-KHI-01": (4, 3, Decimal("17750.50")),
        "BR-LHE-01": (3, 2, Decimal("15000.00")),
        "BR-ISB-01": (2, 1, Decimal("2500.00")),
        "BR-PEW-01": (0, 0, Decimal("0.00")),
        "BR-QTA-01": (0, 0, Decimal("0.00")),
    }
    # Multiple members/receipts must not multiply each other through a join.
    for branch in register(user):
        assert (
            branch.member_count,
            branch.unsent_count,
            branch.unsent_amount,
        ) == expected[branch.code]
        assert isinstance(branch.unsent_amount, Decimal)
        dashboard = kpis.k4((2026, 10), AS_OF, [branch.pk])
        assert branch.unsent_count == dashboard["count"]
        assert branch.unsent_amount == dashboard["amount"]
    # The seed includes voided and transferred receipts, and inactive/left members.
    assert Collection.objects.filter(voided_at__isnull=False).exists()
    assert Collection.objects.filter(transfer_id__isnull=False).exists()
    assert Member.objects.filter(status=MemberStatus.INACTIVE).exists()
    assert Member.objects.filter(status=MemberStatus.LEFT).exists()


@pytest.mark.parametrize(
    "prefix,members,money,codes,status",
    [
        ("superadmin", True, True, {"KHI", "LHE", "ISB", "PEW", "QTA"}, 200),
        ("finance", False, True, {"KHI", "LHE", "ISB", "PEW", "QTA"}, 200),
        ("branchlead", True, True, {"KHI"}, 200),
        ("hr", True, False, {"KHI", "LHE", "ISB"}, 200),
        ("content", False, False, set(), 403),
        (None, False, False, set(), 302),
    ],
)
def test_t_rbac_branch_register_counts(client, prefix, members, money, codes, status):
    if prefix:
        user = User.objects.get(email=f"{prefix}.demo@shiplens.test")
        client.force_login(user)
    response = client.get(reverse("branch-list"))
    assert response.status_code == status
    if status != 200:
        return
    rows = list(response.context["branches"])
    assert {branch.city.code for branch in rows} == codes
    for branch in rows:
        assert (branch.member_count is not None) == members
        assert (branch.unsent_count is not None) == money
        assert (branch.unsent_amount is not None) == money
    for label, visible in (("Members", members), ("Unsent", money)):
        cells = re.findall(
            rf'<td[^>]*data-label="{label}"[^>]*>(.*?)</td>', response.text, re.S
        )
        assert len(cells) == len(rows)
        assert all(("—" not in cell) == visible for cell in cells)
    khi = Branch.objects.get(code="BR-KHI-01")
    detail = client.get(reverse("branch-detail", args=[khi.pk]))
    assert detail.status_code == 200
    assert (detail.context["branch"].member_count is not None) == members
    assert (detail.context["branch"].unsent_amount is not None) == money


@pytest.mark.parametrize("language", ["en", "ur"])
def test_branch_counts_money_and_empty_zeros(client, language):
    client.force_login(User.objects.get(role=Role.SUPER_ADMIN))
    khi = Branch.objects.get(code="BR-KHI-01")
    response = client.get(f"/{language}/app/branches/{khi.pk}/")
    assert response.status_code == 200
    assert "Rs 17,750.50" in response.text
    assert "<bdi>3</bdi>" in response.text
    empty = Branch.objects.get(code="BR-PEW-01")
    response = client.get(f"/{language}/app/branches/{empty.pk}/")
    assert response.status_code == 200
    assert "Rs 0.00" in response.text
    assert response.text.count("<bdi>0</bdi>") == 2


def test_counts_remain_scoped_if_branch_list_is_global(monkeypatch, client):
    monkeypatch.setitem(PERMISSIONS["branch.list"], Role.BRANCH_LEAD, GLOBAL)
    user = User.objects.get(email="branchlead.demo@shiplens.test")
    client.force_login(user)
    response = client.get(reverse("branch-list"))
    rows = list(response.context["branches"])
    assert len(rows) == 5
    for branch in rows:
        if branch.code == "BR-KHI-01":
            assert branch.member_count == 4 and branch.unsent_count == 3
        else:
            assert branch.member_count is None
            assert branch.unsent_count is None and branch.unsent_amount is None


@pytest.mark.parametrize("branch_count", [2, 20])
def test_t_brn_count_query_count_is_constant(
    branch_factory, django_assert_num_queries, branch_count
):
    user = User.objects.get(role=Role.SUPER_ADMIN)
    role = VolunteerRole.objects.get(code="VOLUNTEER")
    created = [
        branch_factory(
            code=f"BR-KHI-{number + 2:02d}",
            name_en=f"Count branch {number}",
            status=BranchStatus.ACTIVE,
            opened_on=date(2026, 10, 1),
        )
        for number in range(branch_count)
    ]
    Member.objects.bulk_create(
        [
            Member(
                member_id=f"M-2026-{branch.pk * 10 + index:05d}",
                branch=branch,
                volunteer_role=role,
                full_name="Count Fixture",
                email=f"count-{branch.pk}-{index}@example.test",
                phone="+923000000999",
                joined_on=date(2026, 10, 1),
                created_by=user,
                updated_by=user,
            )
            for branch in created
            for index in range(2)
        ]
    )
    Collection.objects.bulk_create(
        [
            Collection(
                reference=f"COL-{branch.code}-{index:05d}",
                branch=branch,
                collection_date=AS_OF.date(),
                amount=Decimal("10.50"),
                method="CASH",
                receipt_no=f"COUNT-{index}",
                created_by=user,
            )
            for branch in created
            for index in range(3)
        ]
    )
    queryset = register(user).filter(pk__in=[branch.pk for branch in created])
    with django_assert_num_queries(1):
        rows = list(queryset)
    assert len(rows) == branch_count
    assert all(row.member_count == 2 for row in rows)
    assert all(row.unsent_count == 3 for row in rows)
    assert all(row.unsent_amount == Decimal("31.50") for row in rows)
