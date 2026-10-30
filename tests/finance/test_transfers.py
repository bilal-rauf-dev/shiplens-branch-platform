from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from html.parser import HTMLParser
from threading import Barrier
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, connections, transaction
from django.urls import reverse
from django.utils import translation

from apps.audit.models import AuditLog
from apps.core import clock as business_clock
from apps.core.exceptions import InvalidTransition
from apps.finance import services
from apps.finance.models import Collection, Transfer

pytestmark = pytest.mark.django_db


def send(bl, branch, item, **kwargs):
    values = {
        "collection_ids": [item.pk],
        "transfer_date": business_clock.today(),
        "bank_reference": "BANK-123",
    }
    values.update(kwargs)
    return services.create_transfer(bl, branch, **values)


def test_transfer_total_and_audit(bl, branch, collection, collection_data):
    second = services.create_collection(
        bl,
        branch,
        {**collection_data, "receipt_no": "SECOND", "amount": Decimal("25.01")},
    )
    transfer = send(bl, branch, collection, collection_ids=[collection.pk, second.pk])
    assert (
        transfer.reference == "TRF-BR-KHI-01-0001"
        and transfer.total_amount == Decimal("125.01")
    )
    assert transfer.collections.count() == 2
    assert AuditLog.objects.filter(action="collection.sent").count() == 2
    assert (
        AuditLog.objects.get(action="transfer.created").after["total_amount"]
        == "125.01"
    )
    collection.refresh_from_db()
    assert collection.state == "SENT"
    with pytest.raises(InvalidTransition):
        services.void_collection(bl, collection, "Duplicate receipt")


@pytest.mark.parametrize(
    "invalid", ["empty", "mixed", "voided", "sent", "early", "future", "bank"]
)
def test_t_xfer_rules(bl, branch, collection, branch_factory, invalid):
    kwargs = {}
    if invalid == "empty":
        kwargs["collection_ids"] = []
    elif invalid == "mixed":
        other = branch_factory(code="BR-LHE-01")
        foreign = Collection.objects.create(
            reference="COL-BR-LHE-01-00001",
            branch=other,
            collection_date=business_clock.today(),
            amount=Decimal("10.00"),
            method="CASH",
            receipt_no="FOREIGN",
            created_by=bl,
        )
        kwargs["collection_ids"] = [collection.pk, foreign.pk]
    elif invalid == "voided":
        services.void_collection(bl, collection, "Duplicate receipt")
    elif invalid == "sent":
        send(bl, branch, collection)
    elif invalid == "early":
        kwargs["transfer_date"] = collection.collection_date - timedelta(days=1)
    elif invalid == "future":
        kwargs["transfer_date"] = business_clock.today() + timedelta(days=1)
    else:
        kwargs["bank_reference"] = "ab"
    count = Transfer.objects.count()
    with pytest.raises((ValidationError, InvalidTransition)):
        send(bl, branch, collection, **kwargs)
    assert Transfer.objects.count() == count


def test_locked_but_unsent_can_still_be_sent(bl, branch, collection, clock):
    clock.shift(timedelta(days=8))
    assert collection.is_locked
    transfer = send(bl, branch, collection)
    collection.refresh_from_db()
    assert collection.transfer_id == transfer.pk and collection.state == "SENT"


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE collections SET amount = amount + 1 WHERE id = %s",
        "UPDATE collections SET collection_date = collection_date + 1 WHERE id = %s",
        "UPDATE collections SET method = 'CHEQUE' WHERE id = %s",
        "UPDATE collections SET branch_id = branch_id + 10000 WHERE id = %s",
        "UPDATE transfers SET bank_reference = 'changed' WHERE id = %s",
        "DELETE FROM transfers WHERE id = %s",
    ],
)
def test_t_xfer_immutable_raw_sql(bl, branch, collection, statement):
    transfer = send(bl, branch, collection)
    with pytest.raises(DatabaseError, match="immutable"), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                statement, [transfer.pk if "transfers" in statement else collection.pk]
            )


def test_transfer_selection_preview_and_prg(client, bl, branch, collection):
    client.force_login(bl)
    response = client.get(reverse("collection-list"), {"state": "UNSENT"})
    assert 'name="collections"' in response.text
    response = client.get(reverse("transfer-prepare"), {"collections": [collection.pk]})
    assert response.status_code == 302
    preview = client.get(response.url)
    assert "100.00" in preview.text and collection.reference in preview.text
    response = client.post(
        reverse("transfer-create", kwargs={"branch_pk": branch.pk}),
        {
            "collections": [collection.pk],
            "transfer_date": business_clock.today(),
            "bank_reference": "BANK-123",
            "note": "Friday deposit",
        },
    )
    assert response.status_code == 302
    detail = client.get(response.url)
    assert (
        "Transfer created." in detail.text
        and "100.00" in detail.text
        and "Friday deposit" in detail.text
    )
    assert client.get(reverse("transfer-list")).status_code == 200
    assert (
        client.post(
            reverse("transfer-create", kwargs={"branch_pk": branch.pk}),
            {
                "collections": [collection.pk],
                "transfer_date": business_clock.today(),
                "bank_reference": "BANK-AGAIN",
            },
        ).status_code
        == 409
    )
    assert not client.get(reverse("collection-list"), {"state": "UNSENT"}).context[
        "collections"
    ]


def test_transfer_audit_failure_rolls_back(bl, branch, collection):
    with patch(
        "apps.finance.services.audit.record", side_effect=RuntimeError("unavailable")
    ):
        with pytest.raises(RuntimeError):
            send(bl, branch, collection)
    collection.refresh_from_db()
    assert collection.transfer_id is None and not Transfer.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_t_xfer_double(bl, branch, collection):
    barrier = Barrier(2)

    def attempt(_index):
        try:
            barrier.wait(timeout=10)
            try:
                send(bl, branch, collection)
                return "sent"
            except InvalidTransition:
                return "conflict"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, range(2)))
    assert sorted(results) == ["conflict", "sent"]
    assert Transfer.objects.count() == 1
    assert AuditLog.objects.filter(action="collection.sent").count() == 1


class TransferCheckboxes(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.values = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if (
            tag == "input"
            and attributes.get("type") == "checkbox"
            and attributes.get("name") == "collections"
        ):
            self.values.append(attributes["value"])


@pytest.mark.parametrize("language", ["en", "ur"])
def test_collection_ids_remain_unformatted_through_transfer_prepare(
    client, bl, branch, collection_data, language
):
    Collection.objects.create(
        id=1000,
        reference="COL-BR-KHI-01-01000",
        branch=branch,
        created_by=bl,
        **{**collection_data, "amount": Decimal("12345.50")},
    )
    client.force_login(bl)
    with translation.override(language):
        page = client.get(reverse("collection-list"), {"state": "UNSENT"})
        assert page.status_code == 200
        selected = TransferCheckboxes(page.text).values
        assert selected == ["1000"]
        assert 'value="1,000"' not in page.text
        assert "Rs 12,345.50" in page.text
        prepared = client.get(reverse("transfer-prepare"), {"collections": selected})
        assert prepared.status_code == 302
        assert parse_qs(urlsplit(prepared.url).query)["collections"] == ["1000"]
        preview = client.get(prepared.url)
        assert preview.status_code == 200
        assert 'name="collections" value="1000"' in preview.text
        assert "Rs 12,345.50" in preview.text
