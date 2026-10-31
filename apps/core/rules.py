"""Read current database overrides, falling back to deployment defaults."""

from contextlib import contextmanager
from contextvars import ContextVar

from django.conf import settings

from apps.core.models import SystemSetting

_request_values = ContextVar("request_rule_values", default=None)


@contextmanager
def request_snapshot():
    """Reuse overrides for one request; reset even when the response fails."""
    token = _request_values.set({})
    try:
        yield
    finally:
        _request_values.reset(token)


def _snapshot_overrides():
    snapshot = _request_values.get()
    if snapshot is None:
        return None
    if "overrides" not in snapshot:
        snapshot["overrides"] = dict(SystemSetting.objects.values_list("key", "value"))
    return snapshot["overrides"]


def get(name):
    """Look up a named rule, raising KeyError for misspelled or unknown names."""
    overrides = _snapshot_overrides()
    if overrides is not None:
        return overrides[name] if name in overrides else settings.BUSINESS_RULES[name]
    override = SystemSetting.objects.filter(key=name).first()
    if override is not None:
        return override.value
    return settings.BUSINESS_RULES[name]


def get_many(names):
    """Read a form's deployment defaults and current overrides in one query."""
    values = {name: settings.BUSINESS_RULES[name] for name in names}
    overrides = _snapshot_overrides()
    if overrides is None:
        overrides = dict(
            SystemSetting.objects.filter(key__in=names).values_list("key", "value")
        )
    values.update({name: overrides[name] for name in names if name in overrides})
    return values
