"""Business rule defaults; persisted overrides are added in P2."""

from django.conf import settings


def get(name):
    """Look up a named rule, raising KeyError for misspelled or unknown names."""
    return settings.BUSINESS_RULES[name]
