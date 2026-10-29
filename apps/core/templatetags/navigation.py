"""Resolve active navigation sections from Django route names, without JavaScript."""

from django import template

register = template.Library()

# Detail and action routes belong to their list's navigation section. The finance
# review queue is separate from the weekly report list, so it has its own pill.
SECTIONS = {
    "content-list": (
        "content-list",
        "content-create",
        "content-edit",
        "content-preview",
        "content-publish",
        "content-unpublish",
        "content-archive",
        "content-restore",
    ),
    "user-list": (
        "user-list",
        "user-create",
        "user-detail",
        "user-edit",
        "user-deactivate",
        "user-reactivate",
        "user-reset-password",
        "user-assign-branch",
        "user-remove-branch",
    ),
    "settings-view": ("settings-view", "settings-update", "demo-reset"),
    "volunteer-role-list": (
        "volunteer-role-list",
        "volunteer-role-create",
        "volunteer-role-edit",
        "volunteer-role-deactivate",
    ),
    "audit-list": ("audit-list", "audit-detail", "audit-verify"),
    "branch-list": (
        "branch-list",
        "branch-detail",
        "branch-create",
        "branch-edit",
        "branch-transition",
        "city-list",
        "city-create",
        "city-edit",
    ),
    "application-list": (
        "application-list",
        "application-detail",
        "application-accept",
        "application-decline",
        "application-reassign",
    ),
    "team-list": ("team-list", "team-create", "team-edit", "team-deactivate"),
    "member-list": (
        "member-list",
        "member-detail",
        "member-edit",
        "member-deactivate",
        "member-reactivate",
        "member-mark-left",
        "member-reinstate",
    ),
    "collection-list": (
        "collection-list",
        "collection-detail",
        "collection-create",
        "collection-edit",
        "collection-void",
    ),
    "transfer-list": (
        "transfer-list",
        "transfer-detail",
        "transfer-create",
        "transfer-prepare",
    ),
    "report-list": (
        "report-list",
        "report-detail",
        "report-save",
        "report-submit",
        "report-resubmit",
        "report-return",
        "report-approve",
    ),
    "volunteer-apply": ("volunteer-apply", "volunteer-thanks"),
}


@register.simple_tag(takes_context=True)
def nav_current(context, route_name):
    """Mark one current destination per navigation, including related detail pages."""
    request = context.get("request")
    match = getattr(request, "resolver_match", None)
    if match is None:
        return False
    return match.url_name in SECTIONS.get(route_name, (route_name,))
