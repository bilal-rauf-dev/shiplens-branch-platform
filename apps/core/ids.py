"""Allocate business identifiers without consuming rolled-back counter values."""

from django.db import connection

from apps.core import clock
from apps.core.models import IdSequence


def next_value(key):
    """Lock and increment a named counter in the caller's transaction. BR-001."""
    if not connection.in_atomic_block:
        raise AssertionError("ids.next_value() requires transaction.atomic()")
    # get_or_create catches a competing insert's IntegrityError inside its own
    # savepoint, retrieves that row and leaves the caller's transaction usable.
    IdSequence.objects.get_or_create(key=key)
    sequence = IdSequence.objects.select_for_update().get(pk=key)
    sequence.last_value += 1
    sequence.updated_at = clock.now()
    sequence.save(update_fields=["last_value", "updated_at"])
    return sequence.last_value
