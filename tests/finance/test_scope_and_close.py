from datetime import timedelta

import pytest
from django.urls import reverse

from apps.accounts.models import Role, User, UserBranchAssignment
from apps.branches import services as branch_services
from apps.branches.models import BranchStatus
from apps.core import clock as business_clock
from apps.finance import services

pytestmark = pytest.mark.django_db


@pytest.fixture
def other_records(branch_factory, collection_data):
    branch = branch_factory(code="BR-LHE-01", status=BranchStatus.ACTIVE)
    lead = User.objects.create_user(
        email="other-finance@example.com",
        full_name="Other finance",
        role=Role.BRANCH_LEAD,
    )
    UserBranchAssignment.objects.create(user=lead, branch=branch, created_by=lead)
    item = services.create_collection(lead, branch, collection_data)
    transfer = services.create_transfer(
        lead, branch, [item.pk], business_clock.today(), "BANK-OTHER"
    )
    unsent = services.create_collection(
        lead, branch, {**collection_data, "receipt_no": "OTHER-UNSENT"}
    )
    return {
        "branch": branch,
        "lead": lead,
        "item": item,
        "transfer": transfer,
        "unsent": unsent,
    }


def test_t_rbac_scope_col(client, bl, branch, collection, other_records):
    client.force_login(bl)
    response = client.get(reverse("collection-list"))
    assert (
        collection.reference in response.text
        and other_records["item"].reference not in response.text
    )
    assert (
        client.get(
            reverse("collection-detail", args=[other_records["item"].pk])
        ).status_code
        == 404
    )
    assert (
        client.get(
            reverse("collection-edit", args=[other_records["item"].pk])
        ).status_code
        == 404
    )
    assert (
        client.get(
            reverse("transfer-detail", args=[other_records["transfer"].pk])
        ).status_code
        == 404
    )
    assert (
        other_records["transfer"].reference
        not in client.get(reverse("transfer-list")).text
    )
    assert (
        client.get(
            reverse("transfer-create", kwargs={"branch_pk": other_records["branch"].pk})
        ).status_code
        == 404
    )
    response = client.get(reverse("transfer-create", kwargs={"branch_pk": branch.pk}))
    assert other_records["unsent"].reference not in response.text
    assert other_records["unsent"].pk not in set(
        response.context["form"]
        .fields["collections"]
        .queryset.values_list("pk", flat=True)
    )
    assert collection.pk in set(
        response.context["form"]
        .fields["collections"]
        .queryset.values_list("pk", flat=True)
    )


def test_finance_reviewer_reads_all_and_cannot_write(
    client, bl, branch, collection, other_records
):
    bl.role = Role.FINANCE_REVIEWER
    bl.save(update_fields=["role"])
    client.force_login(bl)
    response = client.get(reverse("collection-list"))
    assert response.context["paginator"].count == 3
    assert other_records["item"].reference in response.text
    assert (
        client.get(
            reverse("transfer-detail", args=[other_records["transfer"].pk])
        ).status_code
        == 200
    )
    assert (
        client.get(reverse("collection-detail", args=[collection.pk])).status_code
        == 200
    )
    assert (
        "Edit collection"
        not in client.get(reverse("collection-detail", args=[collection.pk])).text
    )
    for route, kwargs in [
        ("collection-create", {"branch_pk": branch.pk}),
        ("collection-edit", {"pk": collection.pk}),
        ("collection-void", {"pk": collection.pk}),
        ("transfer-create", {"branch_pk": branch.pk}),
        ("transfer-prepare", {}),
    ]:
        assert client.post(reverse(route, kwargs=kwargs)).status_code == 403


@pytest.mark.parametrize("role", [Role.HR_LEAD, Role.CONTENT_EDITOR])
def test_hr_and_ce_denied_everywhere_in_finance(
    client, bl, branch, collection, other_records, role
):
    bl.role = role
    bl.save(update_fields=["role"])
    client.force_login(bl)
    for route, kwargs in [
        ("collection-list", {}),
        ("collection-detail", {"pk": collection.pk}),
        ("collection-create", {"branch_pk": branch.pk}),
        ("collection-edit", {"pk": collection.pk}),
        ("collection-void", {"pk": collection.pk}),
        ("transfer-list", {}),
        ("transfer-detail", {"pk": other_records["transfer"].pk}),
        ("transfer-create", {"branch_pk": branch.pk}),
        ("transfer-prepare", {}),
    ]:
        assert client.get(reverse(route, kwargs=kwargs)).status_code == 403
        assert client.post(reverse(route, kwargs=kwargs)).status_code == 403


def test_branch_close_blocked_until_sent(client, bl, branch, collection):
    admin = User.objects.create_user(
        email="close-admin@example.com", full_name="Close admin", role=Role.SUPER_ADMIN
    )
    client.force_login(admin)
    url = reverse("branch-transition", kwargs={"pk": branch.pk, "action": "close"})
    response = client.post(url, {"reason": "Branch work completed"})
    assert response.status_code == 409
    assert "1" in response.text and "100.00" in response.text and "PKR" in response.text
    services.create_transfer(
        bl, branch, [collection.pk], business_clock.today(), "BANK-CLOSE"
    )
    response = client.post(url, {"reason": "Branch work completed"})
    assert response.status_code == 302
    branch.refresh_from_db()
    assert branch.status == BranchStatus.CLOSED


def test_locked_unsent_blocks_but_voided_does_not(bl, branch, collection, clock):
    clock.shift(timedelta(days=8))
    assert branch_services.close_blockers(branch)
    clock.shift(-timedelta(days=8))
    services.void_collection(bl, collection, "Duplicate receipt")
    assert branch_services.close_blockers(branch) == []
