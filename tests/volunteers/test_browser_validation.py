import re
from datetime import date, timedelta
from html.parser import HTMLParser

import pytest
from django.urls import reverse

from apps.accounts.forms import ChangePasswordForm, LoginForm, UserCreateForm
from apps.branches.forms import BranchCreateForm, BranchEditForm, CityCreateForm
from apps.volunteers.forms import ApplicationForm, age_on, birth_date_bounds
from apps.volunteers.models import Application

pytestmark = pytest.mark.django_db


class Fields(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.fields = {}
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in {"input", "textarea", "select"} and "name" in attributes:
            self.fields[attributes["name"]] = attributes


def test_public_form_native_constraints(client):
    response = client.get(reverse("volunteer-apply"))
    fields = Fields(response.text).fields
    assert fields["email"]["type"] == "email"
    assert fields["email"]["maxlength"] == "254"
    assert fields["phone"]["type"] == "tel"
    assert fields["phone"]["inputmode"] == "tel"
    for name, minimum, maximum in (
        ("full_name", "3", "100"),
        ("motivation", "20", "1000"),
    ):
        assert fields[name]["minlength"] == minimum
        assert fields[name]["maxlength"] == maximum
    assert fields["date_of_birth"]["min"] == "1925-10-26"
    assert fields["date_of_birth"]["max"] == "2010-10-25"
    for name in ("full_name", "email", "phone", "motivation", "privacy_consent"):
        assert "required" in fields[name]


@pytest.mark.parametrize(
    "phone",
    [
        "03001234567",
        "+923001234567",
        "923001234567",
        "0300 123-4567",
        "+92-300-1234567",
        "92 300 123 4567",
    ],
)
def test_phone_pattern_accepts_supported_formats(phone):
    pattern = ApplicationForm().fields["phone"].widget.attrs["pattern"]
    assert re.fullmatch(pattern, phone)


@pytest.mark.parametrize("phone", ["02001234567", "+123001234567", "0300123456x"])
def test_phone_pattern_rejects_invalid_formats(phone):
    pattern = ApplicationForm().fields["phone"].widget.attrs["pattern"]
    assert not re.fullmatch(pattern, phone)


@pytest.mark.parametrize(
    "today", [date(2026, 10, 25), date(2028, 2, 29), date(2029, 2, 28)]
)
def test_birth_bounds_include_exact_completed_birthdays(today):
    earliest, latest = birth_date_bounds(today, 16, 100)
    assert age_on(earliest, today) == 100
    assert age_on(earliest - timedelta(days=1), today) == 101
    assert age_on(latest, today) == 16
    assert age_on(latest + timedelta(days=1), today) == 15


def test_birth_bounds_follow_configured_age_rule(settings, clock):
    settings.BUSINESS_RULES = {**settings.BUSINESS_RULES, "min_volunteer_age": 18}
    clock.move_to("2028-02-29T12:00:00+05:00")
    assert ApplicationForm().fields["date_of_birth"].widget.attrs["max"] == "2010-02-28"


@pytest.mark.parametrize(
    "field,value",
    [
        ("full_name", "Al"),
        ("full_name", "A" * 101),
        ("motivation", "A" * 19),
        ("motivation", "A" * 1001),
        ("phone", "abc"),
        ("email", "bad-email"),
        ("date_of_birth", "2011-10-25"),
        ("date_of_birth", "1925-10-25"),
        ("privacy_consent", ""),
    ],
)
def test_direct_post_still_rejects_invalid_input(client, post_data, field, value):
    response = client.post(reverse("volunteer-apply"), {**post_data, field: value})
    assert response.status_code == 200
    assert field in response.context["form"].errors
    assert not Application.objects.exists()


def test_login_and_staff_form_native_constraints(admin):
    login = Fields(LoginForm(request=None).as_p()).fields
    assert login["email"]["type"] == "email"
    assert login["email"]["maxlength"] == "254"
    assert "required" in login["email"] and "required" in login["password"]
    user = Fields(UserCreateForm().as_p()).fields
    assert user["full_name"]["maxlength"] == "100"
    assert user["email"]["type"] == "email"
    password = Fields(ChangePasswordForm(admin).as_p()).fields
    for name in ("new_password1", "new_password2"):
        assert password[name]["minlength"] == "12"
        assert "required" in password[name]
    for form in (BranchCreateForm(), BranchEditForm()):
        fields = Fields(form.as_p()).fields
        assert fields["email"]["type"] == "email"
        assert fields["phone"]["type"] == "tel"
        assert fields["phone"]["inputmode"] == "tel"
        assert re.fullmatch(fields["phone"]["pattern"], "+923001234567")
    code = Fields(CityCreateForm().as_p()).fields["code"]
    assert code["minlength"] == code["maxlength"] == "3"
