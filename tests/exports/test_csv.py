import csv
import io
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext

from apps.accounts.models import Role, User
from apps.audit.models import AuditLog
from apps.exports.registry import EXPORTS
from apps.exports.views import cell
from apps.finance import selectors
from apps.finance.models import Collection

pytestmark = pytest.mark.django_db


def download(client, code, params=None):
    response = client.get(reverse(f"export-{code}-csv"), params or {})
    assert response.status_code == 200
    content = b"".join(response.streaming_content)
    assert content.startswith(b"\xef\xbb\xbf")
    return response, list(csv.reader(io.StringIO(content.decode("utf-8-sig"))))


def sign_in(client, role):
    user = User.objects.filter(role=role).order_by("pk").first()
    client.force_login(user)
    return user


def test_t_exp_csv_collections(client, sample_data):
    user = sign_in(client, Role.BRANCH_LEAD)
    response, rows = download(client, "collections", {"date_from": "2026-10-01"})
    assert rows[0][0] == "Reference"
    assert (
        len(rows) - 1
        == selectors.search_collections(user, {"date_from": "2026-10-01"}).count()
    )
    assert {row[1] for row in rows[1:]} == {"BR-KHI-01"}
    assert "BR-LHE-01" not in str(rows)
    assert any("5250.50" in row for row in rows)
    assert (
        "shiplens_collections_BR-KHI-01_2026-10_20261031T2300.csv"
        in response["Content-Disposition"]
    )
    assert "no-store" in response["Cache-Control"]


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@", "\t", "\r"])
def test_t_exp_csv_injection(client, sample_data, prefix):
    sign_in(client, Role.SUPER_ADMIN)
    payload = prefix + 'HYPERLINK("a,b")\nnext'
    Collection.objects.filter(receipt_no="C05").update(source_note=payload)
    _, rows = download(client, "collections")
    entry = next(row for row in rows if row[5] == "C05")
    assert entry[6] == "'" + payload
    assert cell(Decimal("-12345.50")) == "-12345.50"


def test_t_exp_csv_ur(client, sample_data):
    sign_in(client, Role.SUPER_ADMIN)
    _, rows = download(client, "collections", {"lang": "ur"})
    with translation.override("ur"):
        assert rows[0] == [
            gettext(str(header)) for header, getter in EXPORTS["collections"].columns
        ]
    assert (
        AuditLog.objects.filter(action="export.csv").latest("pk").metadata["lang"]
        == "ur"
    )


def test_t_aud_export(client, sample_data):
    sign_in(client, Role.SUPER_ADMIN)
    _, rows = download(client, "audit")
    event = AuditLog.objects.filter(action="export.csv").latest("pk")
    assert event.metadata == {
        "export_code": "X7",
        "filters": {
            "date_from": None,
            "date_to": None,
            "actor": "",
            "role": "",
            "action": "",
            "entity_type": "",
            "entity": "",
            "branch": None,
        },
        "row_count": len(rows) - 1,
        "lang": "en",
    }
    assert not any(row[3] == "export.csv" for row in rows[1:])


@pytest.mark.parametrize("code", ["unsent", "reports", "summary", "members"])
def test_catalogue_csv_matches_shared_selector(client, sample_data, code):
    user = sign_in(client, Role.SUPER_ADMIN)
    spec = EXPORTS[code]
    params = {"period": "2026-10"} if code in {"summary", "unsent"} else {}
    form = spec.form_fn(user, params)
    assert form.is_valid()
    expected = list(spec.rows_fn(user, form.cleaned_data))
    _, rows = download(client, code, params)
    assert len(rows) == len(expected) + 1
    if code == "summary":
        assert sum(Decimal(row[2]) for row in rows[1:]) == Decimal("73250.50")


def test_export_rate_limit_is_shared_by_user(client, sample_data, settings):
    sign_in(client, Role.SUPER_ADMIN)
    settings.BUSINESS_RULES = {**settings.BUSINESS_RULES, "export_rate_per_hour": 2}
    download(client, "collections")
    download(client, "summary")
    response = client.get(reverse("export-unsent-csv"))
    assert response.status_code == 429
    sign_in(client, Role.FINANCE_REVIEWER)
    download(client, "collections")


def test_export_rejects_invalid_filters_without_audit(client, sample_data):
    sign_in(client, Role.SUPER_ADMIN)
    count = AuditLog.objects.filter(action="export.csv").count()
    response = client.get(reverse("export-collections-csv"), {"date_from": "invalid"})
    assert response.status_code == 400
    assert AuditLog.objects.filter(action="export.csv").count() == count
