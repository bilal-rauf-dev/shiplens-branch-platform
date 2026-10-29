from django import template
from django.utils.safestring import mark_safe

from apps.cms.sanitizing import sanitize

register = template.Library()


@register.filter
def render_cms(value):
    """The only safe-HTML boundary: sanitize again before trusting stored CMS HTML."""
    return mark_safe(sanitize(value or ""))  # noqa: S308 -- BR-123's sole safe boundary.
