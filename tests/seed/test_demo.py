from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, transaction
from django.urls import NoReverseMatch, Resolver404, resolve, reverse

from apps.accounts.models import User
from apps.accounts.selectors import role_home_name
from apps.audit.models import AuditLog
from apps.audit.selectors import verify_chain
from apps.branches.models import Branch, City
from apps.core.models import IdSequence, SystemSetting
from apps.finance.models import Collection, Transfer, WeeklyReport, WeeklyReportLine
from apps.seed import services
from apps.volunteers.models import Application, Member, Team, VolunteerRole
from tests.accounts.conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db(transaction=True)


def counts():
    return {
        model.__name__: model.objects.count()
        for model in (
            User,
            Branch,
            City,
            Member,
            Application,
            Team,
            VolunteerRole,
            Collection,
            Transfer,
            WeeklyReport,
            WeeklyReportLine,
            AuditLog,
            IdSequence,
            SystemSetting,
        )
    }


def test_t_seed_idempotent():
    call_command("seed_demo", if_empty=True)
    before = counts()
    tip = AuditLog.objects.latest("pk").hash
    marker = SystemSetting.objects.get(key="demo_seeded").value
    call_command("seed_demo", if_empty=True)
    assert counts() == before
    assert AuditLog.objects.latest("pk").hash == tip
    assert SystemSetting.objects.get(key="demo_seeded").value == marker


@pytest.mark.parametrize("enabled,password", [(False, TEST_PASSWORD), (True, "short")])
def test_t_seed_demo_only(settings, enabled, password):
    settings.DEMO_MODE, settings.DEMO_PASSWORD = enabled, password
    with pytest.raises(CommandError):
        call_command("seed_demo", reset=True)
    assert not User.objects.exists()


def test_t_seed_users(client):
    call_command("seed_demo")
    for prefix in ("superadmin", "finance", "content", "branchlead", "hr"):
        user = User.objects.get(email=f"{prefix}.demo@shiplens.test")
        assert user.is_demo and not user.must_change_password
        response = client.post(
            reverse("account-login"), {"email": user.email, "password": TEST_PASSWORD}
        )
        assert response.status_code == 302
        assert response.url == reverse(role_home_name(user))
        assert client.get(response.url).status_code == 200
        client.logout()


def test_demo_reset_restores_counts_and_a_valid_protected_chain():
    call_command("seed_demo")
    before = counts()
    admin = User.objects.get(role="SUPER_ADMIN")
    SystemSetting.objects.create(key="collection_lock_days", value=3, updated_by=admin)
    call_command("seed_demo", reset=True)
    assert counts() == before
    assert not SystemSetting.objects.filter(key="collection_lock_days").exists()
    assert verify_chain() == (True, None)
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditLog.objects.update(action="tampered")


def test_demo_reset_failure_restores_data_sequences_and_trigger_guards(monkeypatch):
    call_command("seed_demo")
    before = counts()
    tip = AuditLog.objects.latest("pk").hash

    def fail(*args, **kwargs):
        raise ValueError("import failed after truncate")

    monkeypatch.setattr(services, "import_sample_data", fail)
    with pytest.raises(CommandError, match="import failed"):
        call_command("seed_demo", reset=True)
    assert counts() == before
    assert AuditLog.objects.latest("pk").hash == tip
    assert verify_chain() == (True, None)
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditLog.objects.update(action="tampered")


def test_startup_is_idempotent():
    output = StringIO()
    call_command("startup", stdout=output)
    before = counts()
    call_command("startup", stdout=output)
    assert counts() == before
    assert "skipped" in output.getvalue()


@pytest.mark.parametrize("language", ["en", "ur"])
@pytest.mark.parametrize("enabled", [True, False])
def test_reset_has_no_http_route_or_settings_control(
    client, settings, language, enabled
):
    call_command("seed_demo")
    client.force_login(User.objects.get(role="SUPER_ADMIN"))
    settings.DEMO_MODE = enabled
    with pytest.raises(NoReverseMatch):
        reverse("demo-reset")
    path = f"/{language}/app/demo/reset/"
    with pytest.raises(Resolver404):
        resolve(path)
    page = client.get(f"/{language}/app/settings/")
    assert page.status_code == 200
    assert "/app/demo/reset/" not in page.text
    assert "Reset demo data" not in page.text
    assert "نمائشی ڈیٹا بحال کریں" not in page.text
    before = AuditLog.objects.count()
    assert client.get(path).status_code == 404
    assert client.post(path).status_code == 404
    assert AuditLog.objects.count() >= before


def test_non_demo_startup_does_not_seed(settings):
    settings.DEMO_MODE = False
    call_command("startup", stdout=StringIO())
    assert not User.objects.exists()
