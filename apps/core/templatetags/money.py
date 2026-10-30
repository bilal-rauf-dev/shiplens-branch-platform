"""One currency presentation for both interface languages."""

from decimal import Decimal

from django import template
from django.utils.translation import gettext

register = template.Library()


@register.filter
def money(value):
    """Keep decimal arithmetic and Western digits regardless of the active locale."""
    if value is None:
        return "—"
    amount = format(Decimal(str(value)), ",.2f")
    return gettext("Rs %(amount)s") % {"amount": amount}
