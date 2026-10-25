"""Read current database overrides, falling back to deployment defaults."""

from django.conf import settings

from apps.core.models import SystemSetting


def get(name):
    """Look up a named rule, raising KeyError for misspelled or unknown names."""
    override = SystemSetting.objects.filter(key=name).first()
    if override is not None:
        return override.value
    return settings.BUSINESS_RULES[name]
