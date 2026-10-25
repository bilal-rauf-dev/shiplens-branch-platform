from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import StringIO
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.signals import user_login_failed
from django.core.cache import cache
from django.core.management import CommandError, call_command
from django.db import DatabaseError, connection, connections, transaction
from django.http import HttpResponse

from apps import audit
from apps.accounts import services as account_services
from apps.accounts.models import Role, User
from apps.audit.context import request_context
from apps.audit.middleware import AuditContextMiddleware
from apps.audit.models import AuditLog
from apps.audit.selectors import verify_chain
from apps.audit.services import GENESIS_HASH, canonical_json, diff, record_denial
from apps.core.middleware import RequestIdMiddleware

PASSWORD = "Wicker!Forest-72-Prism"  # noqa: S105 -- test-only credential.
NEW_PASSWORD = "Cobalt!Harbor-83-Pine"  # noqa: S105 -- test-only credential.


@pytest.fixture
def operator(db):
    return User.objects.create_user(
        email="audit@example.com",
        full_name="Audit Operator",
        role=Role.SUPER_ADMIN,
        password=PASSWORD,
    )


@pytest.mark.django_db(transaction=True)
def test_t_aud_requires_atomic():
    with pytest.raises(AssertionError, match="requires transaction.atomic"):
        audit.record(None, "settings.updated")


@pytest.mark.django_db
def test_t_aud_atomic(clock):
    with pytest.raises(RuntimeError), transaction.atomic():
        audit.record(None, "settings.updated", after={"collection_lock_days": 9})
        raise RuntimeError("rollback the setting and its event")
    assert not AuditLog.objects.exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE audit_log SET actor_label = 'tampered'",
        "DELETE FROM audit_log",
        "TRUNCATE TABLE audit_log",
    ],
)
def test_t_aud_immutable(statement):
    with transaction.atomic():
        event = audit.record(None, "settings.updated")
    with pytest.raises(DatabaseError, match="append-only"), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(statement)
    assert AuditLog.objects.filter(pk=event.pk).exists()
    assert verify_chain() == (True, None)


@pytest.mark.django_db(transaction=True)
def test_t_aud_chain(operator, clock):
    assert verify_chain() == (True, None)
    with transaction.atomic():
        first = audit.record(
            operator,
            "user.updated",
            entity=operator,
            before={"full_name": "Previous"},
            after={"full_name": operator.full_name},
        )
        second = audit.record(
            None, "settings.updated", metadata={"amount": Decimal("12.30")}
        )
    assert first.prev_hash == GENESIS_HASH
    assert second.prev_hash == first.hash
    assert first.entity_type == "user"
    assert first.entity_id == operator.pk
    assert first.entity_label == operator.email
    assert str(first) == f"{first.pk}: user.updated"
    assert verify_chain() == (True, None)
    with connection.cursor() as cursor:
        cursor.execute("ALTER TABLE audit_log DISABLE TRIGGER audit_guard_change")
        try:
            cursor.execute(
                "UPDATE audit_log SET actor_label = %s WHERE id = %s",
                ["tampered", first.pk],
            )
        finally:
            cursor.execute("ALTER TABLE audit_log ENABLE TRIGGER audit_guard_change")
    assert verify_chain() == (False, first.pk)
    with pytest.raises(CommandError, match=str(first.pk)):
        call_command("verify_audit_chain")


@pytest.mark.django_db(transaction=True)
def test_t_aud_chain_concurrent_writers():
    barrier = Barrier(2)

    def write_event(index):
        try:
            barrier.wait(timeout=10)
            with transaction.atomic():
                return audit.record(
                    None, "settings.updated", metadata={"writer": index}
                ).pk
        finally:
            connections["default"].close()

    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(write_event, index) for index in range(2)]
        ids = [future.result(timeout=20) for future in futures]
    assert len(set(ids)) == 2
    assert AuditLog.objects.count() == 2
    assert verify_chain() == (True, None)


@pytest.mark.django_db
def test_t_aud_redact_and_diff():
    before = {"unchanged": 1, "name": "Old", "password": "old", "removed": True}
    after = {"unchanged": 1, "name": "New", "password": "new", "added": True}
    changed_before, changed_after = diff(before, after)
    assert "unchanged" not in changed_before
    assert "unchanged" not in changed_after
    assert changed_before["removed"] is True
    assert changed_after["added"] is True
    with transaction.atomic():
        event = audit.record(
            None,
            "user.updated",
            before=before,
            after=after,
            metadata={
                "API_TOKEN": "hidden",
                "nested": [{"clientSecret": "hidden"}],
                "safe": "kept",
                "password_hint": "hidden",
            },
        )
    redaction_marker = "[REDACTED]"
    assert event.before["password"] == redaction_marker
    assert event.after["password"] == redaction_marker
    assert event.metadata == {
        "API_TOKEN": "[REDACTED]",
        "nested": [{"clientSecret": "[REDACTED]"}],
        "safe": "kept",
        "password_hint": "[REDACTED]",
    }
    assert "hidden" not in canonical_json(event.metadata)
    assert verify_chain() == (True, None)


def test_canonical_json_is_sorted_and_supports_business_types():
    identifier = UUID("90d250cb-213b-45de-9368-c088de2fb150")
    moment = datetime(2026, 10, 25, tzinfo=UTC)
    assert canonical_json({"z": identifier, "a": Decimal("12.30")}) == (
        '{"a":"12.30","z":"90d250cb-213b-45de-9368-c088de2fb150"}'
    )
    assert moment.isoformat() in canonical_json({"time": moment})
    with pytest.raises(TypeError, match="Unsupported audit value"):
        canonical_json({"value": object()})


@pytest.mark.django_db
def test_request_context_is_captured_and_reset(rf, operator):
    observed = []

    def view(request):
        with transaction.atomic():
            observed.append(audit.record(None, "auth.login_failed"))
        return HttpResponse()

    request = rf.post(
        "/en/accounts/login/",
        HTTP_X_FORWARDED_FOR="198.51.100.1, 203.0.113.9",
        HTTP_USER_AGENT="X" * 250,
        HTTP_X_REQUEST_ID=str(uuid4()),
    )
    request.user = AnonymousUser()
    response = RequestIdMiddleware(AuditContextMiddleware(view))(request)
    event = observed[0]
    assert event.ip == "203.0.113.9"
    assert event.user_agent == "X" * 200
    assert str(event.request_id) == response["X-Request-ID"]
    assert event.actor_label == "anonymous"
    assert request_context.get() is None
    assert verify_chain() == (True, None)
    request.user = operator
    RequestIdMiddleware(AuditContextMiddleware(view))(request)
    assert observed[1].actor_label == "system"


def test_request_context_resets_after_exception(rf):
    def fail(request):
        raise RuntimeError("test exception")

    request = rf.get("/en/")
    request.user = AnonymousUser()
    with pytest.raises(RuntimeError):
        AuditContextMiddleware(fail)(request)
    assert request_context.get() is None


@pytest.mark.django_db
def test_verify_command_and_system_context():
    with transaction.atomic():
        event = audit.record(None, "settings.updated")
    assert event.actor_label == "system"
    assert event.actor_id is None
    assert event.ip is None
    assert event.request_id is None
    output = StringIO()
    call_command("verify_audit_chain", stdout=output)
    assert "Audit chain is valid" in output.getvalue()


def test_t_aud_security(client, operator, clock):
    client.post("/en/accounts/login/", {"email": operator.email, "password": "wrong"})
    failure = AuditLog.objects.get(action="auth.login_failed")
    assert failure.metadata == {"email": operator.email}
    assert failure.actor_label == "anonymous"
    assert "wrong" not in canonical_json(failure.metadata)
    client.post("/en/accounts/login/", {"email": operator.email, "password": PASSWORD})
    success = AuditLog.objects.get(action="auth.login_succeeded")
    assert success.actor_id == operator.pk
    assert client.session[SESSION_KEY] == str(operator.pk)
    client.post(
        "/en/accounts/change-password/",
        {
            "old_password": PASSWORD,
            "new_password1": NEW_PASSWORD,
            "new_password2": NEW_PASSWORD,
        },
    )
    assert (
        AuditLog.objects.filter(action="auth.password_changed", actor=operator).count()
        == 1
    )
    client.post("/en/accounts/logout/")
    assert AuditLog.objects.filter(action="auth.logout", actor=operator).count() == 1
    assert verify_chain() == (True, None)


def test_t_aud_security_lockout(client, operator, clock):
    for _ in range(5):
        client.post(
            "/en/accounts/login/", {"email": operator.email, "password": "wrong"}
        )
    assert AuditLog.objects.filter(action="auth.login_failed").count() == 5
    locked = AuditLog.objects.get(action="auth.locked_out")
    assert locked.metadata == {"email": operator.email}
    assert verify_chain() == (True, None)


def test_t_aud_denied(client, operator, clock):
    cache.clear()
    client.force_login(operator, backend="apps.accounts.backends.EmailBackend")
    for _ in range(3):
        assert client.get("/en/app/my-branch/").status_code == 403
    assert AuditLog.objects.filter(action="permission.denied").count() == 1
    clock.shift(timedelta(seconds=59))
    client.get("/en/app/my-branch/")
    assert AuditLog.objects.filter(action="permission.denied").count() == 1
    clock.shift(timedelta(seconds=1))
    client.get("/ur/app/my-branch/")
    assert AuditLog.objects.filter(action="permission.denied").count() == 2
    event = AuditLog.objects.filter(action="permission.denied").latest("pk")
    assert event.metadata == {"route": "dashboard-branch", "action": "dashboard.branch"}
    record_denial(operator, "another-route", "user.list")
    assert AuditLog.objects.filter(action="permission.denied").count() == 3
    other = User.objects.create_user(
        email="another@example.com", full_name="Another Operator", role=Role.SUPER_ADMIN
    )
    record_denial(other, "dashboard-branch", "dashboard.branch")
    assert AuditLog.objects.filter(action="permission.denied").count() == 4
    assert verify_chain() == (True, None)


@pytest.mark.django_db
def test_failed_login_without_request_records_only_normalized_email():
    user_login_failed.send(
        sender="test",
        credentials={"email": "MIXED@example.com", "password": "hidden"},
        request=None,
    )
    event = AuditLog.objects.get()
    assert event.metadata == {"email": "mixed@example.com"}
    assert event.actor_label == "system"


def test_t_aud_atomic_auth_signal(operator, rf, client):
    request = rf.post("/en/accounts/login/")
    request.session = client.session
    with pytest.raises(RuntimeError), transaction.atomic():
        operator.backend = "apps.accounts.backends.EmailBackend"
        account_services.sign_in(request, operator)
        assert AuditLog.objects.filter(action="auth.login_succeeded").exists()
        raise RuntimeError("roll back login and audit together")
    operator.refresh_from_db()
    assert operator.last_login is None
    assert not AuditLog.objects.exists()
