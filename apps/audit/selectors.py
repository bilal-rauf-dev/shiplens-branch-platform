"""Read-only verification of the audit chain."""

from apps.audit.models import AuditLog
from apps.audit.services import GENESIS_HASH, _hash


def verify_chain():
    """Verify one ordered database snapshot and identify its first invalid row."""
    previous_hash = GENESIS_HASH
    # One SELECT gives a consistent snapshot even while other transactions append.
    for event in AuditLog.objects.order_by("pk").iterator():
        if event.prev_hash != previous_hash or event.hash != _hash(event):
            return False, event.pk
        previous_hash = event.hash
    return True, None
