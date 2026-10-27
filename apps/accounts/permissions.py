"""The permission table from planning/05, with explicit object scope checks."""

from django.core.exceptions import PermissionDenied

from apps.accounts.models import Role, UserBranchAssignment
from apps.branches.models import Branch

GLOBAL = "GLOBAL"
ASSIGNED = "ASSIGNED"
SA = Role.SUPER_ADMIN
FR = Role.FINANCE_REVIEWER
CE = Role.CONTENT_EDITOR
BL = Role.BRANCH_LEAD
HR = Role.HR_LEAD

# Public actions also list authenticated roles when the matrix allows them.
PUBLIC_ACTIONS = frozenset(
    {
        "public.view",
        "application.submit",
        "account.login",
        "account.set_language",
        "health",
    }
)

PERMISSIONS = {
    "public.view": {SA: GLOBAL, FR: GLOBAL, CE: GLOBAL, BL: GLOBAL, HR: GLOBAL},
    "application.submit": {SA: GLOBAL, FR: GLOBAL, CE: GLOBAL, BL: GLOBAL, HR: GLOBAL},
    "account.login": {},
    "account.logout": {SA: GLOBAL, FR: GLOBAL, CE: GLOBAL, BL: GLOBAL, HR: GLOBAL},
    "account.change_password": {
        SA: GLOBAL,
        FR: GLOBAL,
        CE: GLOBAL,
        BL: GLOBAL,
        HR: GLOBAL,
    },
    "account.set_language": {
        SA: GLOBAL,
        FR: GLOBAL,
        CE: GLOBAL,
        BL: GLOBAL,
        HR: GLOBAL,
    },
    "user.list": {SA: GLOBAL},
    "user.view": {SA: GLOBAL},
    "user.create": {SA: GLOBAL},
    "user.update": {SA: GLOBAL},
    "user.reset_password": {SA: GLOBAL},
    "assignment.manage": {SA: GLOBAL},
    "city.manage": {SA: GLOBAL},
    "volunteer_role.manage": {SA: GLOBAL},
    "settings.view": {SA: GLOBAL},
    "settings.update": {SA: GLOBAL},
    "demo.reset": {SA: GLOBAL},
    "branch.list": {SA: GLOBAL, FR: GLOBAL, BL: ASSIGNED, HR: ASSIGNED},
    "branch.view": {SA: GLOBAL, FR: GLOBAL, BL: ASSIGNED, HR: ASSIGNED},
    "branch.create": {SA: GLOBAL},
    "branch.update": {SA: GLOBAL},
    "branch.transition": {SA: GLOBAL},
    "application.list": {SA: GLOBAL, HR: ASSIGNED},
    "application.view": {SA: GLOBAL, HR: ASSIGNED},
    "application.accept": {HR: ASSIGNED},
    "application.decline": {HR: ASSIGNED},
    "application.reassign_branch": {SA: GLOBAL, HR: ASSIGNED},
    "member.list": {SA: GLOBAL, BL: ASSIGNED, HR: ASSIGNED},
    "member.view": {SA: GLOBAL, BL: ASSIGNED, HR: ASSIGNED},
    "member.update": {SA: GLOBAL, HR: ASSIGNED},
    "member.reinstate": {SA: GLOBAL},
    "team.list": {SA: GLOBAL, BL: ASSIGNED, HR: ASSIGNED},
    "team.manage": {SA: GLOBAL, HR: ASSIGNED},
    "member.export_csv": {SA: GLOBAL, HR: ASSIGNED},
    "collection.list": {SA: GLOBAL, FR: GLOBAL, BL: ASSIGNED},
    "collection.view": {SA: GLOBAL, FR: GLOBAL, BL: ASSIGNED},
    "collection.create": {BL: ASSIGNED},
    "collection.update": {BL: ASSIGNED},
    "collection.void": {BL: ASSIGNED},
    "collection.adjust": {BL: ASSIGNED},
    "transfer.create": {BL: ASSIGNED},
    "transfer.list": {SA: GLOBAL, FR: GLOBAL, BL: ASSIGNED},
    "transfer.view": {SA: GLOBAL, FR: GLOBAL, BL: ASSIGNED},
    "collection.export_csv": {SA: GLOBAL, FR: GLOBAL, BL: ASSIGNED},
    "report.list": {SA: GLOBAL, FR: GLOBAL, BL: ASSIGNED},
    "report.view": {SA: GLOBAL, FR: GLOBAL, BL: ASSIGNED},
    "report.edit_narrative": {BL: ASSIGNED},
    "report.submit": {BL: ASSIGNED},
    "report.resubmit": {BL: ASSIGNED},
    "report.approve": {FR: GLOBAL},
    "report.return": {FR: GLOBAL},
    "report.export_pdf": {SA: GLOBAL, FR: GLOBAL, BL: ASSIGNED},
    "report.export_csv": {SA: GLOBAL, FR: GLOBAL, BL: ASSIGNED},
    "dashboard.head_office": {SA: GLOBAL, FR: GLOBAL},
    "dashboard.branch": {BL: ASSIGNED},
    "dashboard.hr": {HR: ASSIGNED},
    "summary.export_pdf": {SA: GLOBAL, FR: GLOBAL},
    "summary.export_csv": {SA: GLOBAL, FR: GLOBAL},
    "unsent.export_csv": {SA: GLOBAL, FR: GLOBAL, BL: ASSIGNED},
    "audit.list": {SA: GLOBAL},
    "audit.view": {SA: GLOBAL},
    "audit.export_csv": {SA: GLOBAL},
    "audit.verify_chain": {SA: GLOBAL},
    "audit.entity_history": {
        SA: GLOBAL,
        FR: GLOBAL,
        CE: GLOBAL,
        BL: ASSIGNED,
        HR: ASSIGNED,
    },
    "content.list": {SA: GLOBAL, CE: GLOBAL},
    "content.view": {SA: GLOBAL, CE: GLOBAL},
    "content.create": {SA: GLOBAL, CE: GLOBAL},
    "content.update": {SA: GLOBAL, CE: GLOBAL},
    "content.publish": {SA: GLOBAL, CE: GLOBAL},
    "content.unpublish": {SA: GLOBAL, CE: GLOBAL},
    "content.archive": {SA: GLOBAL, CE: GLOBAL},
    "content.restore": {SA: GLOBAL, CE: GLOBAL},
    "health": {SA: GLOBAL, FR: GLOBAL, CE: GLOBAL, BL: GLOBAL, HR: GLOBAL},
}

OWN_ACTIONS = frozenset({"account.change_password", "account.set_language"})

# History is checked against the entity, never against an unrestricted audit row.
ENTITY_VIEW_ACTIONS = {
    "branch": "branch.view",
    "application": "application.view",
    "member": "member.view",
    "team": "team.list",
    "collection": "collection.view",
    "transfer": "transfer.view",
    "weeklyreport": "report.view",
    "contentitem": "content.view",
    "user": "user.view",
}


def assigned_branch_ids(user):
    """Return assignments afresh so revocation takes effect within a session."""
    if not user or not user.is_authenticated or not user.is_active:
        return UserBranchAssignment.objects.none().values_list("branch_id", flat=True)
    return UserBranchAssignment.objects.filter(user_id=user.pk).values_list(
        "branch_id", flat=True
    )


def _scope(user, action):
    if not user or not user.is_authenticated or not user.is_active:
        return None
    return PERMISSIONS.get(action, {}).get(user.role)


def _entity_action(model):
    return ENTITY_VIEW_ACTIONS.get(model._meta.model_name)


def _branch_field(action):
    if action.startswith("branch."):
        return "pk"
    if action.startswith("application."):
        return "preferred_branch_id"
    return "branch_id"


def can(user, action, obj=None):
    """Check the action, then ownership or branch scope when an object is supplied."""
    if action not in PERMISSIONS:
        return False
    if not user or not user.is_authenticated:
        return action in PUBLIC_ACTIONS and (action not in OWN_ACTIONS or obj is None)
    scope = _scope(user, action)
    if scope is None:
        return False
    if obj is None:
        return True  # Route check; object lookup must still use scope_queryset.
    if action in OWN_ACTIONS:
        return obj._meta.label_lower == "accounts.user" and obj.pk == user.pk
    if action == "audit.entity_history":
        entity_action = _entity_action(obj)
        if not _history_entity_allowed(user, entity_action):
            return False
        return bool(entity_action and can(user, entity_action, obj))
    if scope == GLOBAL:
        return True
    branch_id = (
        obj.pk if isinstance(obj, Branch) else getattr(obj, _branch_field(action), None)
    )
    return branch_id is not None and branch_id in assigned_branch_ids(user)


def require(user, action, obj=None):
    """Re-check permission at service boundaries as well as at routes."""
    if not can(user, action, obj):
        raise PermissionDenied


def _history_entity_allowed(user, entity_action):
    if user.role == FR:
        return entity_action in {"collection.view", "transfer.view", "report.view"}
    if user.role == CE:
        return entity_action == "content.view"
    return entity_action is not None


def scope_queryset(user, action, qs, branch_field="branch_id"):
    """Filter before object lookup, so out-of-scope identifiers become 404s."""
    if not can(user, action):
        return qs.none()
    if action in OWN_ACTIONS:
        if qs.model._meta.label_lower != "accounts.user":
            return qs.none()
        return qs.filter(pk=user.pk) if user and user.is_authenticated else qs.none()
    if action == "audit.entity_history":
        entity_action = _entity_action(qs.model)
        if not _history_entity_allowed(user, entity_action):
            return qs.none()
        return scope_queryset(user, entity_action, qs, branch_field)
    if _scope(user, action) != ASSIGNED:
        return qs
    # Branch and application have different relationship names in the data model.
    if branch_field == "branch_id":
        branch_field = _branch_field(action)
    return qs.filter(**{f"{branch_field}__in": assigned_branch_ids(user)})
