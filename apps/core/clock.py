"""One patchable clock for timestamps and Pakistan business dates."""

from zoneinfo import ZoneInfo

from django.utils import timezone

KARACHI = ZoneInfo("Asia/Karachi")


def now():
    """Return an aware timestamp in Asia/Karachi (BR-140, BR-141)."""
    return timezone.now().astimezone(KARACHI)


def today():
    """Return the business date in Pakistan, including around UTC midnight."""
    return now().date()
