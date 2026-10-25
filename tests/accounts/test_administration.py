from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connections
from django.test import Client
from django.urls import reverse

from apps import audit
from apps.accounts import services
from apps.accounts.forms import SystemSettingsForm
from apps.accounts.models import Role, User, UserBranchAssignment
from apps.audit.models import AuditLog
from apps.audit.selectors import verify_chain
from apps.audit.services import canonical_json
from apps.branches.models import Branch, BranchStatus
from apps.core import clock as business_clock
from apps.core import rules
from apps.core.models import SystemSetting
from tests.accounts.conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def frozen_clock(clock):
    return clock


@pytest.fixture
def target():
    return User.objects.create_user(
        email="target@example.com",
        full_name="Target Operator",
        role=Role.BRANCH_LEAD,
        password=TEST_PASSWORD,
    )


@pytest.fixture
def branch():
    return Branch.objects.create(code="BR-KHI-01", name_en="Karachi")


def settings_values(**overrides):
    return {
        "collection_lock_days": 7,
        "allow_submit_current_week": False,
        "min_volunteer_age": 16,
        "apply_rate_per_hour": 5,
        **overrides,
    }


def test_t_config_lockdays(user, clock):
    assert rules.get("collection_lock_days") == 7
    services.update_settings(user, **settings_values(collection_lock_days=3))
    assert rules.get("collection_lock_days") == 3
    row = SystemSetting.objects.get(key="collection_lock_days")
    assert row.updated_by == user
    assert row.updated_at == business_clock.now()
    assert str(row) == "collection_lock_days"
    event = AuditLog.objects.get(action="settings.updated")
    assert event.before == {"collection_lock_days": 7}
    assert event.after == {"collection_lock_days": 3}
    clock.shift(timedelta(minutes=2))
    services.update_settings(user, **settings_values(collection_lock_days=4))
    row.refresh_from_db()
    assert row.updated_at == business_clock.now()
    assert rules.get("collection_lock_days") == 4


@pytest.mark.parametrize(
    "key,value",
    [
        ("collection_lock_days", 0),
        ("collection_lock_days", 31),
        ("min_volunteer_age", 13),
        ("min_volunteer_age", 26),
        ("apply_rate_per_hour", 0),
        ("apply_rate_per_hour", 51),
        ("collection_lock_days", True),
        ("allow_submit_current_week", "false"),
    ],
)
def test_settings_bounds_enforced_by_service(user, key, value):
    with pytest.raises(ValidationError):
        services.update_settings(user, **settings_values(**{key: value}))
    assert not SystemSetting.objects.exists()
    assert not AuditLog.objects.filter(action="settings.updated").exists()


@pytest.mark.parametrize("days,age,rate", [(1, 14, 1), (30, 25, 50)])
def test_settings_accept_boundaries(user, days, age, rate):
    services.update_settings(
        user,
        **settings_values(
            collection_lock_days=days,
            min_volunteer_age=age,
            apply_rate_per_hour=rate,
            allow_submit_current_week=True,
        ),
    )
    assert rules.get("allow_submit_current_week") is True
    assert rules.get("apply_rate_per_hour") == rate
    assert rules.get("min_volunteer_age") == age


def test_settings_whitelist(user):
    with pytest.raises(ValidationError):
        services.update_settings(user, **settings_values(), password_min_length=1)
    with pytest.raises(ValidationError):
        services.update_settings(user, collection_lock_days=3)


def test_create_user_generated_password_and_audit(user):
    created, temporary = services.create_user(
        user, email="NEW@example.com", full_name="New Operator", role=Role.HR_LEAD
    )
    assert created.email == "new@example.com"
    assert created.check_password(temporary)
    assert created.password.startswith("argon2$")
    assert created.must_change_password
    assert created.updated_at == business_clock.now()
    event = AuditLog.objects.get(action="user.created")
    assert event.actor == user
    assert temporary not in canonical_json(event.after)
    assert created.password not in canonical_json(event.after)
    with pytest.raises(ValidationError):
        services.create_user(
            user, email=created.email.upper(), full_name="Other", role=Role.HR_LEAD
        )


@pytest.mark.parametrize("change", ["demote", "deactivate"])
def test_last_active_super_admin_protected(user, change):
    # An inactive SA must not count as an administrative fallback.
    User.objects.create_user(
        email="inactive@example.com",
        full_name="Inactive Admin",
        role=Role.SUPER_ADMIN,
        is_active=False,
    )
    with pytest.raises(ValidationError, match="last active Super Admin"):
        if change == "demote":
            services.update_user(
                user, user, full_name=user.full_name, role=Role.HR_LEAD
            )
        else:
            services.set_user_active(user, user, active=False)
    user.refresh_from_db()
    assert user.is_active
    assert user.role == Role.SUPER_ADMIN


@pytest.mark.parametrize(
    "mutation", ["update", "deactivate", "reactivate", "reset", "assign", "remove"]
)
def test_user_mutations_set_updated_at_from_clock(
    user, target, branch, clock, mutation
):
    if mutation == "remove":
        services.assign_branch(user, target, branch)
    if mutation == "reactivate":
        User.objects.filter(pk=target.pk).update(is_active=False)
    old = target.updated_at
    clock.shift(timedelta(minutes=3))
    if mutation == "update":
        services.update_user(
            user, target, full_name="Updated Operator", role=Role.HR_LEAD
        )
    elif mutation == "deactivate":
        services.set_user_active(user, target, active=False)
    elif mutation == "reactivate":
        services.set_user_active(user, target, active=True)
    elif mutation == "reset":
        target, temporary = services.reset_temporary_password(user, target)
        assert target.check_password(temporary)
        assert target.must_change_password
    elif mutation == "assign":
        services.assign_branch(user, target, branch)
    else:
        services.remove_branch_assignment(user, target, branch.pk)
    target.refresh_from_db()
    assert target.updated_at == business_clock.now()
    assert target.updated_at > old
    assert verify_chain() == (True, None)


@pytest.mark.parametrize(
    "mutation", ["update", "deactivate", "reactivate", "reset", "assign", "remove"]
)
def test_demo_accounts_are_protected(user, target, branch, mutation):
    User.objects.filter(pk=target.pk).update(is_demo=True)
    target.refresh_from_db()
    with pytest.raises(PermissionDenied):
        if mutation == "update":
            services.update_user(user, target, full_name="Edited", role=Role.HR_LEAD)
        elif mutation in {"deactivate", "reactivate"}:
            services.set_user_active(user, target, active=mutation == "reactivate")
        elif mutation == "reset":
            services.reset_temporary_password(user, target)
        elif mutation == "assign":
            services.assign_branch(user, target, branch)
        else:
            services.remove_branch_assignment(user, target, branch.pk)


def test_demo_super_admin_cannot_create_or_promote_super_admin(user, target):
    User.objects.filter(pk=user.pk).update(is_demo=True)
    # The service must re-read the actor rather than trust this stale instance.
    with pytest.raises(PermissionDenied):
        services.create_user(
            user,
            email="extra@example.com",
            full_name="Extra Admin",
            role=Role.SUPER_ADMIN,
        )
    with pytest.raises(PermissionDenied):
        services.update_user(
            user, target, full_name=target.full_name, role=Role.SUPER_ADMIN
        )
    created, _temporary = services.create_user(
        user, email="hr@example.com", full_name="HR Operator", role=Role.HR_LEAD
    )
    assert created.role == Role.HR_LEAD


def test_t_assign_closed(user, target, branch):
    Branch.objects.filter(pk=branch.pk).update(status=BranchStatus.CLOSED)
    with pytest.raises(ValidationError, match="Closed branches"):
        services.assign_branch(user, target, branch)


def test_role_change_revokes_branch_links(user, target, branch):
    services.assign_branch(user, target, branch)
    services.update_user(
        user, target, full_name=target.full_name, role=Role.CONTENT_EDITOR
    )
    assert not UserBranchAssignment.objects.filter(user=target).exists()
    assert (
        AuditLog.objects.filter(
            action="assignment.removed", entity_id__isnull=False
        ).count()
        == 1
    )


def test_admin_mutations_recheck_service_permissions(target, branch):
    with pytest.raises(PermissionDenied):
        services.create_user(
            target, email="bad@example.com", full_name="Wrong Actor", role=Role.HR_LEAD
        )
    with pytest.raises(PermissionDenied):
        services.update_user(
            target, target, full_name=target.full_name, role=Role.HR_LEAD
        )
    with pytest.raises(PermissionDenied):
        services.set_user_active(target, target, active=False)
    with pytest.raises(PermissionDenied):
        services.reset_temporary_password(target, target)
    with pytest.raises(PermissionDenied):
        services.remove_branch_assignment(target, target, branch.pk)
    with pytest.raises(PermissionDenied):
        services.update_settings(target, **settings_values())


def test_deactivation_purges_user_sessions(user, target, clock):
    visitor = Client()
    visitor.force_login(target, backend="apps.accounts.backends.EmailBackend")
    key = visitor.session.session_key
    services.set_user_active(user, target, active=False)
    assert not Session.objects.filter(session_key=key).exists()
    assert visitor.get("/en/app/my-branch/").status_code == 302
    services.set_user_active(user, target, active=True)
    assert visitor.get("/en/app/my-branch/").status_code == 302


def test_admin_write_rolls_back_if_audit_fails(user, target, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("audit insert failed")

    monkeypatch.setattr(audit, "record", fail)
    with pytest.raises(RuntimeError):
        services.update_user(
            user, target, full_name="Must roll back", role=Role.HR_LEAD
        )
    target.refresh_from_db()
    assert target.full_name == "Target Operator"
    with pytest.raises(RuntimeError):
        services.update_settings(user, **settings_values(collection_lock_days=3))
    assert not SystemSetting.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_last_admin_guard_under_concurrent_deactivation():
    admins = [
        User.objects.create_user(
            email=f"admin{index}@example.com", full_name="Admin", role=Role.SUPER_ADMIN
        )
        for index in range(2)
    ]
    barrier = Barrier(2)

    def deactivate(user_id):
        try:
            actor = User.objects.get(pk=user_id)
            barrier.wait(timeout=10)
            try:
                services.set_user_active(actor, actor, active=False)
                return "changed"
            except ValidationError:
                return "protected"
        finally:
            connections["default"].close()

    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(deactivate, admin.pk) for admin in admins]
        results = [future.result(timeout=20) for future in futures]
    assert sorted(results) == ["changed", "protected"]
    assert User.objects.filter(role=Role.SUPER_ADMIN, is_active=True).count() == 1
    assert verify_chain() == (True, None)


def test_admin_http_flow_and_one_response_password(signed_in, target, branch, caplog):
    assert signed_in.get(reverse("user-list")).status_code == 200
    assert signed_in.get(reverse("user-detail", args=[target.pk])).status_code == 200
    response = signed_in.post(
        reverse("user-create"),
        {
            "email": "created@example.com",
            "full_name": "Created User",
            "role": Role.BRANCH_LEAD,
            "is_demo": "true",
            "is_active": "false",
            "password": "ignored",
        },
    )
    assert response.status_code == 200
    temporary = response.context["temporary_password"]
    created = User.objects.get(email="created@example.com")
    assert created.check_password(temporary)
    assert created.is_active and not created.is_demo
    assert "no-store" in response["Cache-Control"]
    assert (
        temporary not in signed_in.get(reverse("user-detail", args=[created.pk])).text
    )
    assert temporary not in str(signed_in.session.items())
    assert temporary not in caplog.text
    assert temporary not in canonical_json(
        list(AuditLog.objects.values("before", "after", "metadata"))
    )
    response = signed_in.post(
        reverse("user-edit", args=[created.pk]),
        {
            "full_name": "Edited User",
            "role": Role.HR_LEAD,
            "email": "ignored@example.com",
            "is_active": "false",
            "is_demo": "true",
            "must_change_password": "false",
        },
    )
    assert response.status_code == 302
    created.refresh_from_db()
    assert (
        created.email == "created@example.com"
        and created.is_active
        and not created.is_demo
    )
    assert (
        signed_in.post(
            reverse("user-assign-branch", args=[created.pk]), {"branch_id": branch.pk}
        ).status_code
        == 302
    )
    assert (
        signed_in.post(
            reverse("user-remove-branch", args=[created.pk, branch.pk])
        ).status_code
        == 302
    )
    response = signed_in.post(reverse("user-reset-password", args=[created.pk]))
    assert response.status_code == 200
    assert response.context["temporary_password"] != temporary
    assert "no-store" in response["Cache-Control"]
    assert (
        signed_in.post(reverse("user-deactivate", args=[created.pk])).status_code == 302
    )
    assert (
        signed_in.post(reverse("user-reactivate", args=[created.pk])).status_code == 302
    )
    assert verify_chain() == (True, None)


def test_settings_http_validation(signed_in):
    assert signed_in.get(reverse("settings-view")).status_code == 200
    invalid = signed_in.post(
        reverse("settings-update"), settings_values(collection_lock_days=31)
    )
    assert invalid.status_code == 200
    assert "collection_lock_days" in invalid.context["form"].errors
    valid = signed_in.post(
        reverse("settings-update"), settings_values(collection_lock_days=3)
    )
    assert valid.status_code == 302
    assert rules.get("collection_lock_days") == 3
    form = SystemSettingsForm(data={"collection_lock_days": "not a number"})
    assert not form.is_valid()


def test_admin_http_guards_and_post_only(signed_in, user, target, branch):
    assert signed_in.post(reverse("user-deactivate", args=[user.pk])).status_code == 409
    assert (
        signed_in.post(
            reverse("user-edit", args=[user.pk]),
            {"full_name": "Admin", "role": Role.HR_LEAD},
        ).status_code
        == 200
    )
    assert (
        signed_in.post(
            reverse("user-edit", args=[target.pk]), {"full_name": ""}
        ).status_code
        == 200
    )
    for name, args in (
        ("user-deactivate", [target.pk]),
        ("user-reactivate", [target.pk]),
        ("user-reset-password", [target.pk]),
        ("user-assign-branch", [target.pk]),
        ("user-remove-branch", [target.pk, branch.pk]),
    ):
        assert signed_in.get(reverse(name, args=args)).status_code == 405
    assert (
        signed_in.post(
            reverse("user-assign-branch", args=[target.pk]), {"branch_id": 99999}
        ).status_code
        == 400
    )
    assert signed_in.get(reverse("user-detail", args=[99999])).status_code == 404
    User.objects.filter(pk=target.pk).update(is_demo=True)
    assert (
        signed_in.post(reverse("user-reset-password", args=[target.pk])).status_code
        == 403
    )


def test_self_password_reset_response_survives_session_revocation(signed_in, user):
    response = signed_in.post(reverse("user-reset-password", args=[user.pk]))
    assert response.status_code == 200
    temporary = response.context["temporary_password"]
    assert SESSION_KEY not in signed_in.session
    response = signed_in.post(
        reverse("account-login"), {"email": user.email, "password": temporary}
    )
    assert response.url == reverse("account-change-password")


def test_login_updates_user_timestamp(client, user, clock):
    clock.shift(timedelta(minutes=5))
    client.post(
        reverse("account-login"), {"email": user.email, "password": TEST_PASSWORD}
    )
    user.refresh_from_db()
    assert user.updated_at == business_clock.now()


def test_password_change_updates_timestamp(signed_in, user, clock):
    clock.shift(timedelta(minutes=5))
    response = signed_in.post(
        reverse("account-change-password"),
        {
            "old_password": TEST_PASSWORD,
            "new_password1": "Spruce!Harbor-92-Lantern",
            "new_password2": "Spruce!Harbor-92-Lantern",
        },
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.updated_at == business_clock.now()


def test_self_deactivation_flushes_session_when_another_admin_exists(
    signed_in, user, target
):
    User.objects.filter(pk=target.pk).update(role=Role.SUPER_ADMIN)
    response = signed_in.post(reverse("user-deactivate", args=[user.pk]))
    assert response.status_code == 302
    assert response.url == reverse("account-login")
    assert SESSION_KEY not in signed_in.session
    assert User.objects.filter(role=Role.SUPER_ADMIN, is_active=True).count() == 1


def test_admin_post_requires_csrf(user):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user, backend="apps.accounts.backends.EmailBackend")
    assert (
        client.post(
            reverse("user-create"),
            {
                "email": "forged@example.com",
                "full_name": "Forged",
                "role": Role.HR_LEAD,
            },
        ).status_code
        == 403
    )
    assert client.post(reverse("settings-update"), settings_values()).status_code == 403
    assert not User.objects.filter(email="forged@example.com").exists()


def test_admin_create_duplicate_email_is_a_form_error(signed_in, target):
    response = signed_in.post(
        reverse("user-create"),
        {
            "email": target.email.upper(),
            "full_name": "Duplicate",
            "role": Role.HR_LEAD,
        },
    )
    assert response.status_code == 200
    assert "email" in response.context["form"].errors


def test_assignment_to_non_branch_role_is_a_conflict(signed_in, user, branch):
    response = signed_in.post(
        reverse("user-assign-branch", args=[user.pk]), {"branch_id": branch.pk}
    )
    assert response.status_code == 409
