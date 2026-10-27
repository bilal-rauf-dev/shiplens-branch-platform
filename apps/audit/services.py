"""Write one append-only chain inside the caller's business transaction."""

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from django.core.cache import cache
from django.db import connection, transaction

from apps.accounts.permissions import require
from apps.audit.context import request_context
from apps.audit.models import AuditLog
from apps.core import clock, rules

GENESIS_HASH = "0" * 64
# A fixed, application-wide PostgreSQL advisory lock, not an object-specific lock.
AUDIT_LOCK_KEY = 1397246288


def _json_default(value):
    if isinstance(value, datetime):
        # PostgreSQL reads timestamptz in UTC, while the business clock is Karachi.
        if value.utcoffset() is not None:
            value = value.astimezone(UTC)
        return value.isoformat()
    if isinstance(value, (Decimal, date, UUID)):
        return str(value)
    raise TypeError(f"Unsupported audit value: {type(value).__name__}")


def canonical_json(value):
    """Use one deterministic representation for both writing and verification."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
        allow_nan=False,
    )


def redact(value):
    """Redact sensitive keys recursively, including inside lists. BR-133."""
    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED]"
                if any(word in key.lower() for word in ("password", "token", "secret"))
                else redact(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value


def diff(before, after):
    """Keep changed fields only, comparing before redaction hides secret changes."""
    keys = before.keys() | after.keys()
    changed = [
        key
        for key in keys
        if key not in before or key not in after or before[key] != after[key]
    ]
    return (
        redact({key: before[key] for key in changed if key in before}),
        redact({key: after[key] for key in changed if key in after}),
    )


def _lock_chain():
    # Task P2 explicitly requires this fixed parameterized SQL lock (BR-132).
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [AUDIT_LOCK_KEY])


def _payload(event):
    return {
        field.attname: getattr(event, field.attname)
        for field in AuditLog._meta.concrete_fields
        if field.name != "hash"
    }


def _hash(event):
    content = event.prev_hash + canonical_json(_payload(event))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def record(
    actor,
    action,
    *,
    entity=None,
    entity_type=None,
    entity_id=None,
    entity_label="",
    branch_id=None,
    before=None,
    after=None,
    metadata=None,
):
    """Append a sanitized event in the caller's transaction. BR-130, BR-132, BR-133."""
    if not connection.in_atomic_block:
        raise AssertionError("audit.record() requires transaction.atomic()")
    context = request_context.get()
    authenticated_actor = actor is not None and actor.is_authenticated
    actor_label = "system"
    if authenticated_actor:
        actor_label = actor.email
    elif context and not context["authenticated"]:
        actor_label = "anonymous"
    if entity is not None:
        entity_type = entity_type or entity._meta.model_name
        entity_id = entity.pk if entity_id is None else entity_id
        entity_label = entity_label or str(entity)
    changed_before, changed_after = diff(before or {}, after or {})
    _lock_chain()
    previous = AuditLog.objects.order_by("-pk").first()
    # Reserve the generated ID before hashing, so the hash covers the entire row.
    # Sequence gaps on rollback are normal and do not break the hash chain.
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT nextval(pg_get_serial_sequence(%s, %s))", ["audit_log", "id"]
        )
        event_id = cursor.fetchone()[0]
    event = AuditLog(
        id=event_id,
        occurred_at=clock.now(),
        actor=actor if authenticated_actor else None,
        actor_label=actor_label,
        actor_role=actor.role if authenticated_actor else "",
        action=action,
        entity_type=entity_type or "",
        entity_id=entity_id,
        entity_label=entity_label[:120],
        branch_id=branch_id,
        before=json.loads(canonical_json(changed_before)),
        after=json.loads(canonical_json(changed_after)),
        metadata=json.loads(canonical_json(redact(metadata or {}))),
        ip=context["ip"] if context else None,
        user_agent=context["user_agent"] if context else "",
        request_id=UUID(context["request_id"])
        if context and context["request_id"]
        else None,
        prev_hash=previous.hash if previous else GENESIS_HASH,
    )
    event.hash = _hash(event)
    event.save(force_insert=True)
    return event


def verify_and_record(actor):
    """Verify and count one stable chain, then audit the result in that transaction."""
    from apps.audit.selectors import verify_chain

    with transaction.atomic():
        require(actor, "audit.verify_chain")
        _lock_chain()
        intact, broken_id = verify_chain()
        count = AuditLog.objects.count()
        record(
            actor,
            "audit.chain_verified",
            metadata={
                "intact": intact,
                "broken_event_id": broken_id,
                "event_count": count,
            },
        )
        return intact, broken_id, count


def record_denial(actor, route_name, action):
    """Limit denied events to one per user and route per minute, across workers."""
    key = hashlib.sha256(f"{actor.pk}:{route_name}".encode()).hexdigest()
    with transaction.atomic():
        _lock_chain()
        window = rules.get("audit_denial_seconds")
        current = clock.now().timestamp()
        cache_key = f"audit-denied:{key}"
        previous = cache.get(cache_key)
        if previous is not None and current - previous < window:
            return
        record(
            actor,
            "permission.denied",
            metadata={"route": route_name, "action": action},
        )
        # DatabaseCache rounds expiry to seconds. Retain the timestamp long enough
        # to enforce the exact boundary ourselves. The advisory lock excludes races.
        cache.set(cache_key, current, timeout=window + 1)
