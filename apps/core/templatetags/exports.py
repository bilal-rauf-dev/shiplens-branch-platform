from django import template

from apps.accounts.permissions import can
from apps.exports.registry import EXPORTS

register = template.Library()


@register.simple_tag(takes_context=True)
def export_allowed(context, code):
    return can(context["request"].user, EXPORTS[code].action)


@register.simple_tag(takes_context=True)
def pdf_allowed(context, code, obj=None):
    return can(context["request"].user, f"{code}.export_pdf", obj)
