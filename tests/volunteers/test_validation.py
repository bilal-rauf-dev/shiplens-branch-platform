from datetime import date

import pytest

from apps.branches.models import BranchStatus
from apps.volunteers.forms import ApplicationForm

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "name,valid",
    [
        ("Al", False),
        ("Ali", True),
        ("A" * 100, True),
        ("A" * 101, False),
        ("عائشہ خان", True),
        ("Anne-Marie O'Brien", True),
        ("Ali2", False),
        ("<script>alert</script>", False),
    ],
)
def test_t_app_validation_name(valid_data, name, valid):
    form = ApplicationForm({**valid_data, "full_name": name})
    assert form.is_valid() == valid, form.errors


def test_name_collapses_spaces_before_length_check(valid_data):
    form = ApplicationForm(
        {**valid_data, "full_name": "  Ayesha " + " " * 110 + " Khan  "}
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["full_name"] == "Ayesha Khan"


@pytest.mark.parametrize(
    "phone,valid",
    [
        ("03001234567", True),
        ("+923001234567", True),
        ("923001234567", True),
        ("03 00-123 4567", True),
        ("+92 300-1234567", True),
        ("0211234567", False),
        ("0300123456", False),
        ("030012345678", False),
        ("+913001234567", False),
        ("+92300letters", False),
    ],
)
def test_t_app_validation_phone(valid_data, phone, valid):
    form = ApplicationForm({**valid_data, "phone": phone})
    assert form.is_valid() == valid, form.errors
    if valid:
        assert form.cleaned_data["phone"] == "+923001234567"


@pytest.mark.parametrize(
    "age,guardian,valid",
    [
        (15, True, False),
        (16, False, False),
        (16, True, True),
        (17, False, False),
        (17, True, True),
        (18, False, True),
        (100, False, True),
        (101, False, False),
    ],
)
def test_t_app_validation_age(valid_data, age, guardian, valid):
    form = ApplicationForm(
        {
            **valid_data,
            "date_of_birth": date(2026 - age, 10, 25),
            "guardian_consent": guardian,
        }
    )
    assert form.is_valid() == valid, form.errors


def test_t_app_validation_future_birth_and_age_rule(valid_data, settings):
    form = ApplicationForm({**valid_data, "date_of_birth": "2026-10-26"})
    assert not form.is_valid()
    settings.BUSINESS_RULES = {**settings.BUSINESS_RULES, "min_volunteer_age": 20}
    form = ApplicationForm({**valid_data, "date_of_birth": "2007-10-25"})
    assert not form.is_valid()


@pytest.mark.parametrize(
    "length,valid", [(19, False), (20, True), (1000, True), (1001, False)]
)
def test_t_app_validation_motivation(valid_data, length, valid):
    form = ApplicationForm({**valid_data, "motivation": " " + "A" * length + " "})
    assert form.is_valid() == valid, form.errors


@pytest.mark.parametrize("interests", [[], ["education"] * 6, ["unknown-program"]])
def test_t_app_validation_interests(valid_data, interests):
    form = ApplicationForm({**valid_data, "interests": interests})
    assert not form.is_valid() and "interests" in form.errors


@pytest.mark.parametrize(
    "field,value",
    [
        ("email", "invalid"),
        ("privacy_consent", False),
        ("availability", []),
        ("availability", ["unknown"]),
        ("preferred_language", "xx"),
    ],
)
def test_t_app_validation_required_choices(valid_data, field, value):
    form = ApplicationForm({**valid_data, field: value})
    assert not form.is_valid() and field in form.errors


@pytest.mark.parametrize("status", [BranchStatus.PAUSED, BranchStatus.CLOSED])
def test_t_app_branch_open(valid_data, branch, status):
    branch.status = status
    branch.save(update_fields=["status"])
    form = ApplicationForm(valid_data)
    assert not form.is_valid() and "preferred_branch" in form.errors


def test_form_normalises_email_and_keeps_only_explicit_fields(valid_data):
    form = ApplicationForm(
        {**valid_data, "status": "ACCEPTED", "reference": "MANUAL", "member": 999}
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["email"] == "ayesha@example.com"
    assert "status" not in form.cleaned_data and "member" not in form.cleaned_data
