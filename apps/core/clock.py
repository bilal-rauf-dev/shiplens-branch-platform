"""One patchable clock for timestamps and Pakistan business dates."""

from contextlib import contextmanager
from contextvars import ContextVar
from zoneinfo import ZoneInfo

from django.utils import timezone

KARACHI = ZoneInfo("Asia/Karachi")
_frozen_instant = ContextVar("business_clock_instant", default=None)


@contextmanager
def frozen_at(aware_datetime):
    """Replay history through real services without changing other contexts' clocks.

    Only the sample-data importer uses this override outside tests. Resetting the
    token restores an enclosing override even when a historical event fails.
    """
    if timezone.is_naive(aware_datetime):
        raise ValueError("The clock override requires an aware datetime.")
    token = _frozen_instant.set(aware_datetime.astimezone(KARACHI))
    try:
        yield
    finally:
        _frozen_instant.reset(token)


def now():
    """Return an aware timestamp in Asia/Karachi (BR-140, BR-141)."""
    instant = _frozen_instant.get()
    return instant if instant is not None else timezone.now().astimezone(KARACHI)


def today():
    """Return the business date in Pakistan, including around UTC midnight."""
    return now().date()
