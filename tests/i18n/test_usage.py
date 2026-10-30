from datetime import timedelta

import pytest
from django.utils import translation
from django.utils.translation import gettext

from apps.accounts.models import User
from apps.core import rules

pytestmark = pytest.mark.django_db


def test_t_i18n_validation_ur(client, sample_data, clock):
    response = client.get("/ur/get-involved/")
    token = response.context["form"].initial["render_token"]
    clock.shift(timedelta(seconds=rules.get("form_min_seconds")))
    response = client.post(
        "/ur/get-involved/",
        {
            "render_token": token,
            "email": "invalid-email",
            "phone": "123",
            "motivation": "too short",
        },
    )
    assert response.status_code == 200
    assert '<html lang="ur" dir="rtl">' in response.text
    with translation.override("ur"):
        required = gettext("This field is required.")
        invalid_email = gettext("Enter a valid email address.")
    assert required != "This field is required."
    assert invalid_email != "Enter a valid email address."
    form = response.context["form"]
    assert required in form.errors["full_name"]
    assert invalid_email in form.errors["email"]
    assert "درست پاکستانی موبائل نمبر درج کریں۔" in form.errors["phone"]
    assert required in response.text
    assert "Enter a valid Pakistani mobile number." not in response.text


def test_urdu_staff_table_and_dashboard(client, sample_data, clock):
    clock.move_to("2026-10-31T23:00:00+05:00")
    client.force_login(User.objects.get(role="SUPER_ADMIN"))
    collections = client.get("/ur/app/collections/")
    dashboard = client.get("/ur/app/dashboard/", {"period": "2026-10"})
    assert collections.status_code == dashboard.status_code == 200
    for page in (collections, dashboard):
        assert '<html lang="ur" dir="rtl">' in page.text
    assert '<h1 class="page-title">وصولیاں</h1>' in collections.text
    assert "5,250.50 روپے" in collections.text
    assert '<h1 class="page-title">مرکزی دفتر کا ڈیش بورڈ</h1>' in dashboard.text
    assert "<bdi>73,250.50 روپے</bdi>" in dashboard.text
    assert "<bdi>BR-KHI-01</bdi>" in dashboard.text
    assert "۷۳٬۲۵۰" not in dashboard.text
