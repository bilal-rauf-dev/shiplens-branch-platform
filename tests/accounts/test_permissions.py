"""Exercise the frozen matrix and scope helpers independently of future routes."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models import F
from django.db.models.deletion import RestrictedError
from django.http import Http404
from django.shortcuts import get_object_or_404

from apps.accounts.models import Role, User, UserBranchAssignment
from apps.accounts.permission_docs import GROUPS, render_permissions
from apps.accounts.permissions import (
    ASSIGNED,
    GLOBAL,
    PERMISSIONS,
    PUBLIC_ACTIONS,
    assigned_branch_ids,
    can,
    require,
    scope_queryset,
)
from apps.accounts.services import assign_branch
from apps.branches.models import Branch, BranchStatus
from apps.core import clock as business_clock

# JSON is a YAML 1.2 subset, readable using the standard library without PyYAML.
EXPECTED = json.loads(
    (Path(__file__).resolve().parents[1] / "rbac_expected.yaml").read_text(
        encoding="utf-8"
    )
)


def test_rbac_matrix_matches_expected():
    assert PERMISSIONS == EXPECTED["permissions"]
    assert PUBLIC_ACTIONS == set(EXPECTED["public_actions"])
    assert all(
        role in Role.values and scope in {GLOBAL, ASSIGNED}
        for assignments in PERMISSIONS.values()
        for role, scope in assignments.items()
    )


@pytest.mark.parametrize("action", EXPECTED["permissions"])
@pytest.mark.parametrize("role", [*Role.values, "ANON"])
def test_t_rbac_matrix_action_grants(action, role):
    principal = (
        AnonymousUser()
        if role == "ANON"
        else SimpleNamespace(is_authenticated=True, is_active=True, role=role)
    )
    expected = (
        action in EXPECTED["public_actions"]
        if role == "ANON"
        else role in EXPECTED["permissions"][action]
    )
    assert can(principal, action) == expected
    if expected:
        require(principal, action)
    else:
        with pytest.raises(PermissionDenied):
            require(principal, action)


def test_permissions_fail_closed():
    for principal in (
        None,
        AnonymousUser(),
        SimpleNamespace(is_authenticated=True, is_active=False, role=Role.SUPER_ADMIN),
        SimpleNamespace(is_authenticated=True, is_active=True, role="UNRECOGNIZED"),
    ):
        assert not can(principal, "unknown.action")
        assert not can(principal, "user.create")
    inactive = SimpleNamespace(
        is_authenticated=True, is_active=False, role=Role.BRANCH_LEAD
    )
    assert not can(inactive, "public.view")


@pytest.fixture
def branches(branch_factory):
    return (
        branch_factory(code="BR-KHI-01", name_en="Karachi"),
        branch_factory(code="BR-LHE-01", name_en="Lahore"),
    )


@pytest.fixture
def lead(user):
    return User.objects.create_user(
        email="lead@example.com", full_name="Branch Lead", role=Role.BRANCH_LEAD
    )


@pytest.mark.django_db
@pytest.mark.parametrize("role", [Role.BRANCH_LEAD, Role.HR_LEAD])
def test_assignment_service_records_creator_once(user, lead, branches, role, clock):
    lead.role = role
    lead.save(update_fields=["role"])
    first = assign_branch(user, lead, branches[0])
    second = assign_branch(user, lead, branches[0])
    assert first.pk == second.pk
    assert first.created_by == user
    assert first.created_at == business_clock.now()
    assert list(assigned_branch_ids(lead)) == [branches[0].pk]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role", [Role.SUPER_ADMIN, Role.FINANCE_REVIEWER, Role.CONTENT_EDITOR]
)
def test_assignment_rejects_non_branch_roles(user, lead, branches, role):
    # The service must re-read the stored role, rather than trust a stale caller.
    User.objects.filter(pk=lead.pk).update(role=role)
    with pytest.raises(ValidationError):
        assign_branch(user, lead, branches[0])
    assert not UserBranchAssignment.objects.exists()


@pytest.mark.django_db
def test_t_rbac_service_assignment_denies_wrong_actor(user, lead, branches):
    for actor in (lead, AnonymousUser()):
        with pytest.raises(PermissionDenied):
            assign_branch(actor, lead, branches[0])
    assert not UserBranchAssignment.objects.exists()


@pytest.mark.django_db
def test_assignment_database_constraints(user, lead, branches):
    assignment = assign_branch(user, lead, branches[0])
    with pytest.raises(IntegrityError), transaction.atomic():
        UserBranchAssignment.objects.create(
            user=lead, branch=branches[0], created_by=user
        )
    for obj in (user, lead, branches[0]):
        with pytest.raises(RestrictedError):
            obj.delete()
    assignment.refresh_from_db()
    with pytest.raises(IntegrityError), transaction.atomic():
        Branch.objects.create(
            code=branches[0].code, name_en="Duplicate", city=branches[0].city
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        Branch.objects.create(
            code="BR-BAD-01", name_en="Invalid", city=branches[0].city, status="UNKNOWN"
        )
    assert str(assignment) == f"{lead.pk}: {branches[0].pk}"
    assert str(branches[0]) == "Karachi"


@pytest.mark.django_db
@pytest.mark.parametrize("role", [Role.BRANCH_LEAD, Role.HR_LEAD])
def test_t_rbac_scope_branch(user, lead, branches, role):
    lead.role = role
    lead.save(update_fields=["role"])
    assert not scope_queryset(lead, "branch.view", Branch.objects.all()).exists()
    assign_branch(user, lead, branches[0])
    scoped = scope_queryset(lead, "branch.view", Branch.objects.all())
    assert list(scoped) == [branches[0]]
    assert can(lead, "branch.view", branches[0])
    assert not can(lead, "branch.view", branches[1])
    with pytest.raises(Http404):
        get_object_or_404(scoped, pk=branches[1].pk)
    with pytest.raises(PermissionDenied):
        require(lead, "branch.view", branches[1])
    assert list(scope_queryset(user, "branch.view", Branch.objects.all())) == list(
        branches
    )
    assert not scope_queryset(
        AnonymousUser(), "branch.view", Branch.objects.all()
    ).exists()
    assert not scope_queryset(lead, "user.list", User.objects.all()).exists()


@pytest.mark.django_db
def test_t_rbac_scope_resources_and_revocation(user, lead, branches):
    assignment = assign_branch(user, lead, branches[0])
    assign_branch(user, lead, branches[1])
    rows = UserBranchAssignment.objects.filter(user=lead)
    for action in ("collection.view", "member.view", "report.export_csv"):
        assert set(scope_queryset(lead, action, rows)) == set(rows)
        assert can(lead, action, assignment)
        assert not can(lead, action, SimpleNamespace(branch_id=None))
    assert set(
        scope_queryset(lead, "branch.view", rows, branch_field="branch__pk")
    ) == set(rows)
    # Revocation is read afresh; a long-lived user instance has no cached grants.
    UserBranchAssignment.objects.filter(pk=assignment.pk).delete()
    assert not can(lead, "collection.view", assignment)
    assert list(assigned_branch_ids(lead)) == [branches[1].pk]
    lead.is_active = False
    assert not assigned_branch_ids(lead).exists()
    assert not assigned_branch_ids(AnonymousUser()).exists()


@pytest.mark.django_db
def test_t_rbac_scope_application_preferred_branch(user, lead, branches):
    lead.role = Role.HR_LEAD
    lead.save(update_fields=["role"])
    assigned = assign_branch(user, lead, branches[0])
    other = UserBranchAssignment.objects.create(
        user=lead, branch=branches[1], created_by=user
    )
    # Exercise the planned application's relationship name using an ORM alias.
    rows = UserBranchAssignment.objects.annotate(preferred_branch_id=F("branch_id"))
    UserBranchAssignment.objects.filter(pk=other.pk).update(user=user)
    scoped = scope_queryset(lead, "application.reassign_branch", rows)
    assert list(scoped) == [assigned]
    assert can(lead, "application.reassign_branch", rows.get(pk=assigned.pk))
    assert not can(lead, "application.reassign_branch", rows.get(pk=other.pk))


@pytest.mark.django_db
@pytest.mark.parametrize("action", ["account.change_password", "account.set_language"])
def test_own_account_scope(user, lead, action):
    assert can(user, action, user)
    assert not can(user, action, lead)
    assert list(scope_queryset(user, action, User.objects.all())) == [user]
    assert not scope_queryset(user, action, Branch.objects.all()).exists()
    assert not scope_queryset(AnonymousUser(), action, User.objects.all()).exists()
    assert not can(AnonymousUser(), action, user)


def entity(model_name, branch_id=None, pk=1):
    return SimpleNamespace(
        _meta=SimpleNamespace(model_name=model_name), branch_id=branch_id, pk=pk
    )


@pytest.mark.django_db
def test_entity_history_preserves_entity_permissions(user, lead, branches):
    assign_branch(user, lead, branches[0])
    financial = entity("collection", branches[0].pk)
    foreign = entity("collection", branches[1].pk)
    assert can(lead, "audit.entity_history", financial)
    assert not can(lead, "audit.entity_history", foreign)
    assert not can(lead, "audit.entity_history", entity("contentitem"))
    assert can(user, "audit.entity_history", financial)
    assert not can(user, "audit.entity_history", entity("unknown"))
    assert list(scope_queryset(lead, "audit.entity_history", Branch.objects.all())) == [
        branches[0]
    ]
    assert not scope_queryset(
        user, "audit.entity_history", UserBranchAssignment.objects.all()
    ).exists()
    for role, allowed in (
        (Role.FINANCE_REVIEWER, "collection"),
        (Role.CONTENT_EDITOR, "contentitem"),
    ):
        lead.role = role
        assert can(lead, "audit.entity_history", entity(allowed))
        assert not can(lead, "audit.entity_history", entity("member", branches[0].pk))
        assert not can(lead, "audit.entity_history", branches[0])
        assert not scope_queryset(
            lead, "audit.entity_history", Branch.objects.all()
        ).exists()
    lead.role = Role.HR_LEAD
    assert can(lead, "audit.entity_history", entity("member", branches[0].pk))
    assert not can(lead, "audit.entity_history", financial)


@pytest.mark.django_db
def test_public_and_denied_querysets(user, branches):
    assert list(
        scope_queryset(AnonymousUser(), "public.view", Branch.objects.all())
    ) == list(branches)
    assert not scope_queryset(user, "unknown.action", Branch.objects.all()).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("status", BranchStatus.values)
def test_branch_status_choices(status, branch_factory):
    branch = branch_factory(code="BR-KHI-01", name_en="Karachi", status=status)
    branch.full_clean()


def test_t_rbac_doc_sync(settings):
    assert (settings.BASE_DIR / "docs" / "permissions.md").read_text(
        encoding="utf-8"
    ) == render_permissions()
    document = render_permissions()
    for group in GROUPS:
        assert f"## {group}" in document
    for action in PERMISSIONS:
        assert f"| `{action}` |" in document


def test_export_permissions_command(tmp_path, settings):
    settings.BASE_DIR = tmp_path
    (tmp_path / "docs").mkdir()
    call_command("export_permissions")
    assert (tmp_path / "docs" / "permissions.md").read_text(
        encoding="utf-8"
    ) == render_permissions()
