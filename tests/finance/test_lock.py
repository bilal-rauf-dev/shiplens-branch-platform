from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.core import clock as business_clock
from apps.core.exceptions import InvalidTransition
from apps.finance import selectors, services
from apps.finance.forms import VoidCollectionForm
from apps.finance.models import Collection

pytestmark = pytest.mark.django_db


@pytest.fixture
def october_entry(bl, branch, collection_data, clock):
    clock.move_to("2026-10-01T10:00:00+05:00")
    return services.create_collection(
        bl, branch, {**collection_data, "collection_date": business_clock.today()}
    )


def data_for(item, **changes):
    values = {
        "collection_date": item.collection_date,
        "amount": item.amount,
        "method": item.method,
        "receipt_no": item.receipt_no,
        "collected_by": item.collected_by_member,
        "source_note": item.source_note,
        **changes,
    }
    return {key: value for key, value in values.items() if value is not None}


def test_collection_editable_on_day_7(bl, october_entry, clock):
    clock.move_to("2026-10-07T18:00:00+05:00")
    assert services.update_collection(
        bl, october_entry, data_for(october_entry, amount=Decimal("120.00"))
    ).amount == Decimal("120.00")


def test_collection_locked_on_day_8(client, bl, october_entry, clock):
    clock.move_to("2026-10-08T12:00:00+05:00")
    client.force_login(bl)
    assert (
        client.post(
            reverse("collection-edit", args=[october_entry.pk]), data_for(october_entry)
        ).status_code
        == 409
    )
    assert (
        client.post(
            reverse("collection-void", args=[october_entry.pk]),
            {"reason": "Duplicate receipt"},
        ).status_code
        == 409
    )
    assert AuditLog.objects.filter(action="collection.edit_denied").count() == 2


@pytest.mark.parametrize(
    "timestamp,editable",
    [("2026-10-08T09:59:59+05:00", True), ("2026-10-08T10:00:00+05:00", False)],
)
def test_t_col_lock_before_and_at(bl, october_entry, clock, timestamp, editable):
    clock.move_to(timestamp)
    if editable:
        assert not october_entry.is_locked
        services.update_collection(
            bl, october_entry, data_for(october_entry, amount=Decimal("101.00"))
        )
    else:
        assert october_entry.state == "LOCKED"
        with pytest.raises(InvalidTransition, match="01|08"):
            services.update_collection(bl, october_entry, data_for(october_entry))
        with pytest.raises(InvalidTransition):
            services.void_collection(bl, october_entry, "Duplicate receipt")
        event = AuditLog.objects.filter(action="collection.edit_denied").latest("pk")
        assert "PKT" in event.metadata["reason"]
        october_entry.amount = Decimal("120.00")
        with pytest.raises(InvalidTransition):
            october_entry.save()


def test_t_col_lock_config(bl, october_entry, clock, settings):
    settings.BUSINESS_RULES = {**settings.BUSINESS_RULES, "collection_lock_days": 3}
    clock.move_to("2026-10-04T10:00:00+05:00")
    assert october_entry.is_locked
    with pytest.raises(InvalidTransition):
        services.void_collection(bl, october_entry, "Duplicate receipt")


def test_t_col_void_and_edit_diff(client, bl, collection):
    updated = services.update_collection(
        bl, collection, data_for(collection, amount=Decimal("125.00"))
    )
    event = AuditLog.objects.filter(action="collection.updated").latest("pk")
    assert event.before == {"amount": "100.00"} and event.after == {"amount": "125.00"}
    assert selectors.totals(Collection.objects.all())["total"] == Decimal("125.00")
    services.void_collection(bl, updated, "Duplicate receipt")
    updated.refresh_from_db()
    assert updated.state == "VOIDED" and updated.voided_by == bl
    assert selectors.totals(Collection.objects.all())["total"] == 0
    client.force_login(bl)
    response = client.get(reverse("collection-list"), {"state": "VOIDED"})
    assert response.status_code == 200 and response.context["totals"]["total"] == 0
    assert list(response.context["collections"]) == [updated]
    with pytest.raises(InvalidTransition):
        services.update_collection(bl, updated, data_for(updated))


def test_t_col_edit_outside_scope_404(client, bl, collection, branch_factory):
    other = branch_factory(code="BR-LHE-01")
    Collection.objects.filter(pk=collection.pk).update(branch=other)
    client.force_login(bl)
    assert (
        client.post(
            reverse("collection-edit", args=[collection.pk]), data_for(collection)
        ).status_code
        == 404
    )


def test_collection_screens_filters_and_prg(client, bl, branch, collection_data):
    client.force_login(bl)
    url = reverse("collection-create", kwargs={"branch_pk": branch.pk})
    assert client.get(url).status_code == 200
    response = client.post(url, collection_data)
    assert response.status_code == 302
    detail = client.get(response.url)
    assert "Collection created." in detail.text and "History" in detail.text
    item = Collection.objects.get()
    response = client.post(
        reverse("collection-edit", args=[item.pk]),
        {**collection_data, "amount": "102.00"},
    )
    assert (
        response.status_code == 302
        and "Collection updated." in client.get(response.url).text
    )
    response = client.get(
        reverse("collection-list"),
        {
            "date_from": "2026-10-25",
            "date_to": "2026-10-25",
            "method": "CASH",
            "state": "OPEN",
        },
    )
    assert response.context["totals"]["total"] == Decimal("102.00")
    assert not client.get(reverse("collection-list"), {"method": "CHEQUE"}).context[
        "collections"
    ]
    assert client.get(reverse("collection-void", args=[item.pk])).status_code == 200
    assert (
        client.post(
            reverse("collection-void", args=[item.pk]), {"reason": "Duplicate receipt"}
        ).status_code
        == 302
    )


def test_week_closed_and_write_rollback(bl, collection):
    with patch("apps.finance.services.week_is_closed", return_value=True):
        with pytest.raises(InvalidTransition):
            services.void_collection(bl, collection, "Duplicate receipt")
    assert AuditLog.objects.filter(action="collection.edit_denied").exists()
    with patch(
        "apps.finance.services.audit.record", side_effect=RuntimeError("unavailable")
    ):
        with pytest.raises(RuntimeError):
            services.update_collection(
                bl, collection, data_for(collection, amount=Decimal("110.00"))
            )
    collection.refresh_from_db()
    assert collection.amount == Decimal("100.00")


def test_void_form_and_service_share_rule_bounds(bl, collection, settings):
    settings.BUSINESS_RULES = {
        **settings.BUSINESS_RULES,
        "collection_void_reason_min_length": 6,
        "collection_void_reason_max_length": 10,
    }
    form = VoidCollectionForm({"reason": "short"})
    assert not form.is_valid()
    assert form.fields["reason"].widget.attrs["minlength"] == 6
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError, match="6 and 10"):
        services.void_collection(bl, collection, "short")
