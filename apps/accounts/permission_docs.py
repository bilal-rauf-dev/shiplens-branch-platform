"""Render the code matrix in the same groups as planning/05 section 3."""

from apps.accounts.models import Role
from apps.accounts.permissions import OWN_ACTIONS, PERMISSIONS, PUBLIC_ACTIONS

GROUPS = (
    "3.1 Public & account",
    "3.2 Administration",
    "3.3 Branches",
    "3.4 Applications & members",
    "3.5 Collections & transfers",
    "3.6 Weekly reports",
    "3.7 Dashboard, exports, audit",
    "3.8 Content manager",
    "3.9 Ops",
)


def _group(action):
    prefix = action.split(".")[0]
    if prefix in {"public", "account"} or action == "application.submit":
        return GROUPS[0]
    if prefix in {"user", "assignment", "city", "volunteer_role", "settings", "demo"}:
        return GROUPS[1]
    if prefix == "branch":
        return GROUPS[2]
    if prefix in {"application", "member", "team"}:
        return GROUPS[3]
    if prefix in {"collection", "transfer"}:
        return GROUPS[4]
    if prefix == "report":
        return GROUPS[5]
    if prefix in {"dashboard", "summary", "unsent", "audit"}:
        return GROUPS[6]
    if prefix == "content":
        return GROUPS[7]
    return GROUPS[8]


def render_permissions():
    """Return deterministic Markdown for review and the documentation sync test."""
    lines = [
        "# Permissions",
        "",
        "Generated — do not edit by hand. Run `python manage.py export_permissions`.",
        "Source: `apps/accounts/permissions.py`; plan: "
        "`docs/planning/05-rbac-matrix.md` §3.",
        "",
        "Legend: GLOBAL = allowed globally; ASSIGNED = assigned branches only;",
        "own = caller's own account; — = denied. Unknown actions are denied.",
        "SA = Super Admin; FR = Finance Reviewer; CE = Content Editor;",
        "BL = Branch Lead; HR = HR Lead; ANON = anonymous.",
        "",
    ]
    for group in GROUPS:
        lines.extend(
            [
                f"## {group}",
                "",
                "| Action | ANON | SA | FR | CE | BL | HR |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for action, assignments in PERMISSIONS.items():
            if _group(action) != group:
                continue
            cells = ["GLOBAL" if action in PUBLIC_ACTIONS else "—"]
            for role in Role:
                cell = assignments.get(role, "—")
                if action in OWN_ACTIONS and role in assignments:
                    cell = "own"
                cells.append(cell)
            lines.append(f"| `{action}` | {' | '.join(cells)} |")
        if group == GROUPS[8]:
            lines.append(
                "| `/admin/` | Disabled; no admin routes installed | | | | | |"
            )
        lines.append("")
    lines.extend(
        [
            "## Scope rules and additional checks",
            "",
            "- Only active authenticated users receive role "
            "permissions; there is no Super Admin bypass.",
            "- Anonymous public access does not grant the same action "
            "to an authenticated role: login is anonymous only.",
            "- `account.change_password` and authenticated "
            "`account.set_language` apply only to the caller. GLOBAL is "
            "the role grant; object/queryset checks enforce ownership.",
            "- Branch queries filter `pk`; applications filter "
            "`preferred_branch_id`; members, teams, collections, "
            "transfers and reports filter `branch_id` by current "
            "assignments.",
            "- Call `scope_queryset` before object lookup so "
            "out-of-scope objects return 404. `require` raises "
            "PermissionDenied at service boundaries.",
            "- `audit.entity_history` receives the underlying entity "
            "(or its queryset), not audit rows. It requires permission "
            "to view that entity. FR is restricted to collections, "
            "transfers and reports; CE to content; BL/HR retain "
            "assigned-branch scope. Unknown entity types are denied.",
            "- HR `application.reassign_branch` scopes the source "
            "application. The reassignment service must separately "
            "validate an open destination branch (destination need not "
            "be assigned).",
            "- Assignments remain available for historical scope after "
            "branch closure; operational state restrictions belong in "
            "services.",
            "- Last-active-Super-Admin, demo-account, DEMO_MODE and "
            "resource-state restrictions are additional service rules, "
            "not broader permission grants.",
            "- `/health` is represented by the public `health` action "
            "and remains exempt from request authorization checks.",
            "",
        ]
    )
    return "\n".join(lines)
