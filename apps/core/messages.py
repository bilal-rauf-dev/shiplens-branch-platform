"""Extraction markers for framework strings our Urdu interface needs.

Django merges project translations over its bundled catalogue. Its Urdu catalogue
leaves some validation, password and help messages empty; these markers let gettext
include our translations without replacing Django's validators or forms.
"""

from django.utils.translation import gettext_noop, ngettext_lazy

FRAMEWORK_MESSAGES = (
    gettext_noop("This field is required."),
    gettext_noop("Enter a valid email address."),
    gettext_noop("Enter a valid integer."),
    gettext_noop("Enter a valid date."),
    gettext_noop("Enter a number."),
    gettext_noop("Enter a whole number."),
    gettext_noop("Enter a valid value."),
    gettext_noop("Null characters are not allowed."),
    gettext_noop(
        "Select a valid choice. That choice is not one of the available choices."
    ),
    gettext_noop(
        "Select a valid choice. %(value)s is not one of the available choices."
    ),
    gettext_noop("Enter a list of values."),
    gettext_noop("Old password"),
    gettext_noop("New password"),
    gettext_noop("New password confirmation"),
    gettext_noop("Password confirmation"),
    gettext_noop("The two password fields didn't match."),
    gettext_noop("Enter the same password as before, for verification."),
    gettext_noop("Your old password was entered incorrectly. Please enter it again."),
    gettext_noop("The password is too similar to the %(verbose_name)s."),
    gettext_noop(
        "Your password can't be too similar to your other personal information."
    ),
    gettext_noop("This password is too common."),
    gettext_noop("Your password can't be a commonly used password."),
    gettext_noop("This password is entirely numeric."),
    gettext_noop("Your password can't be entirely numeric."),
    ngettext_lazy(
        "Ensure this value has at least %(limit_value)d character "
        "(it has %(show_value)d).",
        "Ensure this value has at least %(limit_value)d characters "
        "(it has %(show_value)d).",
        "limit_value",
    ),
    ngettext_lazy(
        "Ensure this value has at most %(limit_value)d character "
        "(it has %(show_value)d).",
        "Ensure this value has at most %(limit_value)d characters "
        "(it has %(show_value)d).",
        "limit_value",
    ),
    ngettext_lazy(
        "Ensure that there are no more than %(max)s digit in total.",
        "Ensure that there are no more than %(max)s digits in total.",
        "max",
    ),
    ngettext_lazy(
        "Ensure that there are no more than %(max)s decimal place.",
        "Ensure that there are no more than %(max)s decimal places.",
        "max",
    ),
    ngettext_lazy(
        "Ensure that there are no more than %(max)s digit before the decimal point.",
        "Ensure that there are no more than %(max)s digits before the decimal point.",
        "max",
    ),
    ngettext_lazy(
        "This password is too short. It must contain at least %d character.",
        "This password is too short. It must contain at least %d characters.",
        "min_length",
    ),
    ngettext_lazy(
        "Your password must contain at least %(min_length)d character.",
        "Your password must contain at least %(min_length)d characters.",
        "min_length",
    ),
)
