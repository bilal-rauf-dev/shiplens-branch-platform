import pytest
from django.conf import settings

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.core import clock as business_clock
from tests.publicsite.test_pages import PATHS

pytestmark = pytest.mark.django_db
STAFF_PATHS = [
    "app/collections/",
    "app/transfers/",
    "app/members/",
    "app/dashboard/",
    "app/audit/",
]


@pytest.mark.parametrize(
    "path", PATHS + ["accounts/login/", "get-involved/thanks/"] + STAFF_PATHS
)
def test_t_i18n_dir(client, sample_data, path):
    if path in STAFF_PATHS:
        client.force_login(User.objects.get(role="SUPER_ADMIN"))
    response = client.get(f"/ur/{path}")
    assert response.status_code == 200
    assert '<html lang="ur" dir="rtl">' in response.text


@pytest.mark.parametrize(
    "path", ["branches/", "programs/education-support/", "app/collections/?state=OPEN"]
)
@pytest.mark.parametrize("source,target", [("en", "ur"), ("ur", "en")])
def test_t_i18n_switch(client, sample_data, path, source, target, clock):
    user = User.objects.get(role="SUPER_ADMIN")
    client.force_login(user)
    response = client.get(f"/{source}/{path}")
    assert response.status_code == 200
    assert f'name="next" value="/{target}/{path}"' in response.text
    response = client.post(
        "/i18n/set-language/", {"language": target, "next": f"/{target}/{path}"}
    )
    assert response.status_code == 302
    assert response.url == f"/{target}/{path}"
    cookie = response.cookies[settings.LANGUAGE_COOKIE_NAME]
    assert cookie.value == target
    assert bool(cookie["secure"]) == settings.LANGUAGE_COOKIE_SECURE
    assert cookie["samesite"] == "Lax"
    user.refresh_from_db()
    assert user.preferred_language == target
    if source == "en":
        assert user.updated_at == business_clock.now()
        assert AuditLog.objects.filter(
            action="user.updated",
            entity_id=str(user.pk),
            after={"preferred_language": target},
        ).exists()


def test_language_switch_ignores_invalid_language_and_external_redirect(
    client, sample_data
):
    user = User.objects.get(role="SUPER_ADMIN")
    client.force_login(user)
    response = client.post(
        "/i18n/set-language/",
        {"language": "invalid", "next": "https://untrusted.example/"},
    )
    assert response.url == "/"
    user.refresh_from_db()
    assert user.preferred_language == "en"
