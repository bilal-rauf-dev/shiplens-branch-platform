from datetime import date
from decimal import Decimal

import pytest
from django.template import Context, Template
from django.utils import formats, translation

from apps.core.templatetags.money import money


@pytest.mark.parametrize(
    "language,expected", [("en", "Rs 12,345.50"), ("ur", "Rs 12,345.50")]
)
def test_money_uses_western_digits_and_locale_currency(language, expected):
    with translation.override(language):
        assert money(Decimal("12345.50")) == expected
        assert (
            Template("{% load money %}<bdi>{{ amount|money }}</bdi>").render(
                Context({"amount": Decimal("12345.50")})
            )
            == f"<bdi>{expected}</bdi>"
        )


def test_money_handles_absent_values():
    assert money(None) == "—"


def test_urdu_dates_and_number_separators():
    with translation.override("ur"):
        assert formats.get_format("DATE_FORMAT") == "j F Y"
        assert formats.date_format(date(2026, 10, 30)) == "30 اکتوبر 2026"
        assert formats.number_format(Decimal("12345.50"), decimal_pos=2) == "12345.50"
        assert (
            formats.number_format(
                Decimal("12345.50"), decimal_pos=2, force_grouping=True
            )
            == "12,345.50"
        )


@pytest.mark.parametrize(
    "value,expected",
    [
        ("invalid-email", "درست ای میل پتہ"),
        ("a" * 255 + "@example.com", "زیادہ سے زیادہ"),
    ],
)
def test_framework_email_validation_is_urdu(value, expected):
    from apps.accounts.forms import UserCreateForm

    with translation.override("ur"):
        form = UserCreateForm(
            {"email": value, "full_name": "Example User", "role": "HR_LEAD"}
        )
        assert not form.is_valid()
        assert expected in str(form.errors["email"])
        assert "Enter a valid email address" not in str(form.errors["email"])


def test_framework_password_validation_is_urdu():
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    with translation.override("ur"):
        with pytest.raises(ValidationError) as error:
            validate_password("123")
        messages = " ".join(error.value.messages)
    assert "بہت چھوٹا" in messages
    assert "صرف ہندسوں" in messages
    assert "This password" not in messages
