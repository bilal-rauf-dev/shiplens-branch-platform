from datetime import date
from html.parser import HTMLParser
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import polib
import pytest
from django.db import connection, transaction
from django.urls import reverse

from apps import audit
from apps.accounts.models import Role, User
from apps.audit import selectors, services
from apps.audit.context import request_context
from apps.audit.models import AuditLog
from apps.volunteers.models import Member, VolunteerRole

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def frozen_audit_clock(clock):
    pass


@pytest.fixture
def sa():
    return User.objects.create_user(
        email="admin-viewer@example.com", full_name="Viewer", role=Role.SUPER_ADMIN
    )


@pytest.fixture
def admin_client(client, sa):
    # Authentication auditing is tested separately; keep this filter dataset exact.
    with patch("apps.audit.signals.record"):
        client.force_login(sa)
    return client


@pytest.fixture
def dataset(sa, branch_factory, clock):
    branch = branch_factory(name_en="Karachi Central")
    other_branch = branch_factory(code="BR-LHE-01", name_en="Lahore East")
    hr = User.objects.create_user(
        email="hr-viewer@example.com", full_name="Reviewer", role=Role.HR_LEAD
    )
    role, _ = VolunteerRole.objects.get_or_create(
        code="VOLUNTEER", defaults={"name_en": "Volunteer", "name_ur": "رضاکار"}
    )
    member = Member.objects.create(
        member_id="M-2026-00001",
        branch=branch,
        volunteer_role=role,
        full_name="Ayesha Khan",
        email="ayesha@example.com",
        phone="+923001234567",
        joined_on=date(2026, 10, 1),
        created_by=sa,
        updated_by=sa,
    )
    specs = [
        ("2026-10-24T18:59:59Z", hr, "member.updated", member, branch.pk),
        ("2026-10-24T19:00:00Z", sa, "branch.updated", branch, branch.pk),
        (
            "2026-10-25T18:59:59.999999Z",
            sa,
            "branch.updated",
            other_branch,
            other_branch.pk,
        ),
        ("2026-10-25T19:00:00Z", hr, "auth.login_failed", None, None),
    ]
    events = []
    for timestamp, actor, action, entity, branch_id in specs:
        clock.move_to(timestamp)
        with transaction.atomic():
            events.append(
                audit.record(
                    actor,
                    action,
                    entity=entity,
                    branch_id=branch_id,
                    before={"notes": "old", "is_active": False},
                    after={"notes": "new", "is_active": True},
                )
            )
    # Restore the login clock after creating events around several midnight edges.
    clock.move_to("2026-10-25T12:00:00+05:00")
    return {
        "events": events,
        "branch": branch,
        "other_branch": other_branch,
        "member": member,
        "hr": hr,
    }


@pytest.mark.parametrize(
    "params,expected",
    [
        ({"date_from": "2026-10-25"}, [1, 2, 3]),
        ({"date_to": "2026-10-25"}, [0, 1, 2]),
        ({"date_from": "2026-10-25", "date_to": "2026-10-25"}, [1, 2]),
        ({"actor": "ADMIN-VIEWER@EXAMPLE"}, [1, 2]),
        ({"role": "HR_LEAD"}, [0, 3]),
        ({"action": "branch.updated"}, [1, 2]),
        ({"entity_type": "member"}, [0]),
        ({"entity": "KARACHI"}, [1]),
    ],
)
def test_t_aud_viewer_each_filter(admin_client, dataset, params, expected):
    response = admin_client.get(reverse("audit-list"), params)
    assert response.status_code == 200
    assert {row["event"].pk for row in response.context["rows"]} == {
        dataset["events"][index].pk for index in expected
    }
    assert response["Cache-Control"] == "no-store, private"


def test_t_aud_viewer_branch_and_entity_id_filters(admin_client, dataset):
    response = admin_client.get(reverse("audit-list"), {"branch": dataset["branch"].pk})
    assert {row["event"].pk for row in response.context["rows"]} == {
        event.pk for event in dataset["events"][:2]
    }
    response = admin_client.get(
        reverse("audit-list"),
        {"entity_type": "member", "entity": str(dataset["member"].pk)},
    )
    assert [row["event"] for row in response.context["rows"]] == [dataset["events"][0]]
    response = admin_client.get(reverse("audit-list"), {"entity": "9" * 120})
    assert response.status_code == 200 and not response.context["rows"]


def test_t_aud_viewer_combined_and_grouped_actions(admin_client, dataset):
    params = {
        "date_from": "2026-10-25",
        "date_to": "2026-10-25",
        "actor": "admin-viewer",
        "role": "SUPER_ADMIN",
        "action": "branch.updated",
        "entity_type": "branch",
        "entity": "Karachi",
        "branch": dataset["branch"].pk,
    }
    response = admin_client.get(reverse("audit-list"), params)
    assert [row["event"] for row in response.context["rows"]] == [dataset["events"][1]]
    assert '<optgroup label="Branches">' in response.text
    assert "auth.login_failed" in response.text
    params["actor"] = "missing@example.com"
    assert not admin_client.get(reverse("audit-list"), params).context["rows"]


@pytest.mark.parametrize(
    "params,field",
    [
        ({"date_from": "bad"}, "date_from"),
        ({"date_from": "2026-10-26", "date_to": "2026-10-25"}, "date_to"),
        ({"branch": -1}, "branch"),
        ({"action": "invented.action"}, "action"),
        ({"role": "ROOT"}, "role"),
        ({"entity_type": "invented"}, "entity_type"),
    ],
)
def test_t_aud_viewer_invalid_filters(admin_client, dataset, params, field):
    response = admin_client.get(reverse("audit-list"), params)
    assert response.status_code == 200 and not response.context["rows"]
    assert field in response.context["filter_form"].errors


class Links(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.links = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs).get("href", ""))


def test_t_aud_viewer_pagination_keeps_filters(admin_client, sa, dataset, clock):
    for index in range(51):
        with transaction.atomic():
            audit.record(
                sa,
                "branch.updated",
                entity=dataset["branch"],
                branch_id=dataset["branch"].pk,
                entity_label="Karachi & Central",
                before={"name": "old"},
                after={"name": f"new {index}"},
            )
    params = {
        "date_from": "2026-10-25",
        "date_to": "2026-10-25",
        "actor": sa.email,
        "role": sa.role,
        "action": "branch.updated",
        "entity_type": "branch",
        "entity": "Karachi &",
        "branch": str(dataset["branch"].pk),
    }
    response = admin_client.get(reverse("audit-list"), params)
    assert len(response.context["rows"]) == 50
    assert response.context["paginator"].count == 51
    ids = [row["event"].pk for row in response.context["rows"]]
    assert ids == sorted(ids, reverse=True)
    next_link = next(link for link in Links(response.text).links if "page=2" in link)
    assert parse_qs(urlsplit(next_link).query) == {
        **{key: [value] for key, value in params.items()},
        "page": ["2"],
    }
    second = admin_client.get(reverse("audit-list") + next_link)
    assert len(second.context["rows"]) == 1
    assert second.context["rows"][0]["event"].pk not in ids


def test_t_aud_viewer_detail_diff_context_and_escape(admin_client, sa, dataset):
    token = request_context.set(
        {
            "authenticated": True,
            "ip": "203.0.113.9",
            "user_agent": "Viewer browser",
            "request_id": "592eb2ec-01b9-4721-8f37-467dd96302dc",
        }
    )
    try:
        with transaction.atomic():
            event = audit.record(
                sa,
                "member.updated",
                entity=dataset["member"],
                branch_id=dataset["branch"].pk,
                before={"notes": "old <script>bad()</script>", "flag": False},
                after={"notes": "new notes", "flag": True},
            )
    finally:
        request_context.reset(token)
    response = admin_client.get(reverse("audit-detail", args=[event.pk]))
    assert response.status_code == 200
    for value in (
        "Before",
        "After",
        "old &lt;script&gt;bad()&lt;/script&gt;",
        "new notes",
        "false",
        "true",
        "203.0.113.9",
        "Viewer browser",
        str(event.request_id),
        event.hash,
        event.prev_hash,
    ):
        assert value in response.text
    assert "<script>bad()" not in response.text
    assert reverse("member-detail", args=[dataset["member"].pk]) in response.text
    assert dataset["branch"].code in response.text
    assert "Delete" not in response.text


def test_entity_link_requires_record_permission(sa, dataset):
    event = dataset["events"][0]
    assert selectors.viewer_rows(sa, [event])[0]["entity_url"] == reverse(
        "member-detail", args=[dataset["member"].pk]
    )
    sa.role = Role.FINANCE_REVIEWER
    assert selectors.viewer_rows(sa, [event])[0]["entity_url"] is None


@pytest.mark.django_db(transaction=True)
def test_t_aud_viewer_verify_intact_and_tampered(admin_client, dataset, sa):
    url = reverse("audit-verify")
    assert admin_client.get(url).status_code == 405
    count = AuditLog.objects.count()
    response = admin_client.post(url)
    assert response.status_code == 302
    assert f"Chain intact ({count} events)" in admin_client.get(response.url).text
    verified = AuditLog.objects.latest("pk")
    assert verified.action == "audit.chain_verified" and verified.actor == sa
    assert verified.metadata == {
        "intact": True,
        "broken_event_id": None,
        "event_count": count,
    }
    assert selectors.verify_chain() == (True, None)
    bad_id = dataset["events"][0].pk
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE audit_log DISABLE TRIGGER audit_guard_change")
            try:
                cursor.execute(
                    "UPDATE audit_log SET entity_label = %s WHERE id = %s",
                    ["tampered", bad_id],
                )
            finally:
                cursor.execute(
                    "ALTER TABLE audit_log ENABLE TRIGGER audit_guard_change"
                )
    response = admin_client.post(url)
    assert f"Chain broken at event #{bad_id}" in admin_client.get(response.url).text
    verified = AuditLog.objects.latest("pk")
    assert (
        verified.metadata["intact"] is False
        and verified.metadata["broken_event_id"] == bad_id
    )


@pytest.mark.parametrize("suffix", ["edit", "delete"])
def test_t_aud_viewer_unknown_mutation_returns_404(admin_client, dataset, suffix):
    event = dataset["events"][0]
    before = list(AuditLog.objects.order_by("pk").values())
    assert admin_client.post(f"/en/app/audit/{event.pk}/{suffix}/").status_code == 404
    assert list(AuditLog.objects.order_by("pk").values()) == before


def test_audit_indexes_cover_required_columns():
    with connection.cursor() as cursor:
        indexes = connection.introspection.get_constraints(cursor, "audit_log")
    for fields in (
        ["occurred_at"],
        ["actor_id"],
        ["action"],
        ["entity_type", "entity_id", "occurred_at"],
        ["branch_id", "occurred_at"],
    ):
        assert any(
            index["index"] and index["columns"] == fields for index in indexes.values()
        )


def test_t_aud_viewer_urdu(admin_client, dataset, settings, tmp_path):
    compiled = tmp_path / "ur/LC_MESSAGES/django.mo"
    compiled.parent.mkdir(parents=True)
    polib.pofile(
        str(settings.BASE_DIR / "locale/ur/LC_MESSAGES/django.po")
    ).save_as_mofile(str(compiled))
    settings.LOCALE_PATHS = [tmp_path]
    response = admin_client.get("/ur/app/audit/")
    assert response.status_code == 200 and 'dir="rtl"' in response.text
    assert "آڈٹ لاگ" in response.text
    assert "سلسلے کی تصدیق کریں" in response.text


def test_verify_audit_failure_rolls_back(sa, dataset):
    count = AuditLog.objects.count()
    with patch("apps.audit.services.record", side_effect=RuntimeError("unavailable")):
        with pytest.raises(RuntimeError):
            services.verify_and_record(sa)
    assert AuditLog.objects.count() == count
