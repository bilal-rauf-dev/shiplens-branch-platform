"""Public form validation follows BR-040 through BR-050."""

import re
import unicodedata
from datetime import timedelta

from django import forms
from django.core import signing
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from apps.core import clock, rules
from apps.volunteers import selectors
from apps.volunteers.constants import AVAILABILITY, INTERESTS
from apps.volunteers.models import ApplicationStatus, MemberStatus, Team, VolunteerRole


def render_token():
    return signing.dumps({"rendered_at": clock.now().timestamp()}, salt="apply-form")


def age_on(date_of_birth, today):
    """Count completed birthdays rather than dividing days by a year length."""
    return (
        today.year
        - date_of_birth.year
        - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
    )


def _years_before(today, years):
    """Use February 28 when a leap-day anniversary falls in a non-leap year."""
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(year=today.year - years, day=28)


def birth_date_bounds(today, minimum_age, maximum_age):
    """Return inclusive dates matching the completed-birthday age check."""
    earliest = _years_before(today, maximum_age + 1) + timedelta(days=1)
    latest = _years_before(today, minimum_age)
    return earliest, latest


class BranchChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, branch):
        name = branch.name_ur if get_language() == "ur" else branch.name_en
        return f"{branch.code} · {name}"


class TeamForm(forms.Form):
    name = forms.CharField(label=_("Team name"), max_length=60)


class MemberEditForm(forms.Form):
    team_id = forms.ModelChoiceField(
        label=_("Team"), queryset=Team.objects.none(), required=False
    )
    role_id = forms.ModelChoiceField(
        label=_("Volunteer role"), queryset=VolunteerRole.objects.none()
    )
    phone = forms.RegexField(
        label=_("Mobile number"),
        regex=r"\A\+923[0-9]{9}\Z",
        max_length=16,
        widget=forms.TextInput(
            attrs={"type": "tel", "inputmode": "tel", "pattern": r"\+923[0-9]{9}"}
        ),
        help_text=_("Use the international format, for example +923001234567."),
    )
    notes = forms.CharField(
        label=_("Notes"), max_length=1000, required=False, widget=forms.Textarea
    )

    def __init__(self, *args, member, **kwargs):
        super().__init__(*args, **kwargs)
        from django.db.models import Q

        self.fields["team_id"].queryset = (
            Team.objects.filter(branch_id=member.branch_id)
            .filter(Q(is_active=True) | Q(pk=member.team_id))
            .order_by("name")
        )
        self.fields["role_id"].queryset = VolunteerRole.objects.filter(
            Q(is_active=True) | Q(pk=member.volunteer_role_id)
        ).order_by("sort_order", "code")


class MemberActionForm(forms.Form):
    pass


class MemberLeftForm(forms.Form):
    left_on = forms.DateField(
        label=_("Left on"), widget=forms.DateInput(attrs={"type": "date"})
    )


class MemberReinstateForm(forms.Form):
    reason = forms.CharField(label=_("Reason"), widget=forms.Textarea)


class VolunteerRoleForm(forms.Form):
    name_en = forms.CharField(label=_("English name"), max_length=60)
    name_ur = forms.CharField(label=_("Urdu name"), max_length=60)
    sort_order = forms.IntegerField(label=_("Sort order"), min_value=0, initial=0)


class MemberFilterForm(forms.Form):
    q = forms.CharField(label=_("Search"), max_length=254, required=False)
    branch = forms.TypedChoiceField(
        label=_("Branch"), coerce=int, empty_value=None, required=False
    )
    team = forms.TypedChoiceField(
        label=_("Team"), coerce=int, empty_value=None, required=False
    )
    role = forms.TypedChoiceField(
        label=_("Volunteer role"), coerce=int, empty_value=None, required=False
    )
    status = forms.ChoiceField(
        label=_("Status"),
        choices=[("", _("All statuses")), *MemberStatus.choices],
        required=False,
    )
    joined_from = forms.DateField(
        label=_("Joined from"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    joined_to = forms.DateField(
        label=_("Joined to"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    sort = forms.ChoiceField(
        label=_("Sort by"),
        required=False,
        choices=[
            ("", _("Newest first")),
            ("name", _("Name (A–Z)")),
            ("-name", _("Name (Z–A)")),
            ("joined", _("Joined date (oldest first)")),
            ("-joined", _("Joined date (newest first)")),
        ],
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        # Materialize each choice list once: validation and rendering reuse it.
        self.fields["branch"].choices = [
            ("", _("All branches")),
            *[
                (
                    branch.pk,
                    f"{branch.code} · "
                    + (branch.name_ur if get_language() == "ur" else branch.name_en),
                )
                for branch in selectors.member_branches(user)
            ],
        ]
        self.fields["team"].choices = [
            ("", _("All teams")),
            *[
                (team.pk, f"{team.branch.code} · {team.name}")
                for team in selectors.member_teams(user)
            ],
        ]
        self.fields["role"].choices = [
            ("", _("All volunteer roles")),
            *[
                (role.pk, role.name_ur if get_language() == "ur" else role.name_en)
                for role in selectors.volunteer_roles()
            ],
        ]

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("joined_from"), cleaned.get("joined_to")
        if start and end and start > end:
            self.add_error(
                "joined_to", _("The end date must be on or after the start date.")
            )
        return cleaned


class ApplicationFilterForm(forms.Form):
    branch_id = BranchChoiceField(
        label=_("Branch"),
        queryset=selectors.accepting_branches().none(),
        required=False,
        empty_label=_("All branches"),
    )
    status = forms.ChoiceField(
        label=_("Status"), choices=ApplicationStatus.choices, required=False
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch_id"].queryset = selectors.review_branches(user)


class VolunteerRoleChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, role):
        return role.name_ur if get_language() == "ur" else role.name_en


class AcceptApplicationForm(forms.Form):
    team_id = forms.ModelChoiceField(
        label=_("Team"), queryset=Team.objects.none(), required=False
    )
    role_id = VolunteerRoleChoiceField(
        label=_("Volunteer role"),
        queryset=VolunteerRole.objects.filter(is_active=True).order_by(
            "sort_order", "code"
        ),
    )

    def __init__(self, *args, application, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["team_id"].queryset = Team.objects.filter(
            branch_id=application.preferred_branch_id, is_active=True
        ).order_by("name")


class DeclineApplicationForm(forms.Form):
    reason = forms.CharField(label=_("Reason"), widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reason"].min_length = rules.get(
            "application_decline_reason_min_length"
        )
        self.fields["reason"].max_length = rules.get(
            "application_decline_reason_max_length"
        )
        self.fields["reason"].widget.attrs.update(
            {
                "minlength": self.fields["reason"].min_length,
                "maxlength": self.fields["reason"].max_length,
            }
        )
        self.fields["reason"].validators.extend(
            [
                MinLengthValidator(self.fields["reason"].min_length),
                MaxLengthValidator(self.fields["reason"].max_length),
            ]
        )


class ReassignApplicationForm(forms.Form):
    branch_id = BranchChoiceField(
        label=_("Target branch"), queryset=selectors.accepting_branches()
    )


class ApplicationForm(forms.Form):
    full_name = forms.CharField(
        label=_("Full name"),
        help_text=_("Use your name, including Urdu letters if preferred."),
    )
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        help_text=_("Enter an email address where HR can contact you."),
    )
    phone = forms.CharField(
        label=_("Mobile number"),
        max_length=64,
        widget=forms.TextInput(
            attrs={
                "type": "tel",
                "inputmode": "tel",
                "autocomplete": "tel",
                "pattern": (
                    r"[\s\-]*(?:0|(?:\+[\s\-]*)?9[\s\-]*2)"
                    r"[\s\-]*3(?:[\s\-]*[0-9]){9}[\s\-]*"
                ),
            }
        ),
        help_text=_("Pakistani mobile number, for example 0300 1234567."),
    )
    date_of_birth = forms.DateField(
        label=_("Date of birth"),
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text=_("Enter your date of birth."),
    )
    guardian_consent = forms.BooleanField(
        label=_("My parent or guardian agrees to my application"),
        required=False,
        help_text=_("Required if you are under 18."),
    )
    preferred_branch = BranchChoiceField(
        label=_("Preferred branch"),
        queryset=selectors.accepting_branches(),
        help_text=_("Choose an Active or Forming branch."),
    )
    interests = forms.MultipleChoiceField(
        label=_("Interests"),
        choices=INTERESTS,
        widget=forms.CheckboxSelectMultiple,
        help_text=_("Choose the areas you are interested in."),
    )
    availability = forms.MultipleChoiceField(
        label=_("Availability"),
        choices=AVAILABILITY,
        widget=forms.CheckboxSelectMultiple,
        help_text=_("Choose at least one time when you can volunteer."),
    )
    motivation = forms.CharField(
        label=_("Why do you want to volunteer?"),
        widget=forms.Textarea,
        help_text=_("Write between 20 and 1000 characters."),
    )
    preferred_language = forms.ChoiceField(
        label=_("Preferred language"),
        choices=[("en", _("English")), ("ur", _("Urdu"))],
        widget=forms.RadioSelect,
        help_text=_("Choose the language you prefer for communication."),
    )
    privacy_consent = forms.BooleanField(
        label=_("I agree to the privacy notice"),
        help_text=_(
            "Your details are used by authorised staff to review your application "
            "and are not shown publicly."
        ),
    )
    website = forms.CharField(
        label=_("Leave this field empty"),
        required=False,
        widget=forms.TextInput(
            attrs={"tabindex": "-1", "autocomplete": "off", "aria-hidden": "true"}
        ),
    )
    render_token = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial.setdefault(
            "preferred_language", "ur" if get_language() == "ur" else "en"
        )
        self.initial.setdefault("render_token", render_token())
        self.fields["full_name"].widget.attrs.update(
            {
                "minlength": rules.get("application_name_min_length"),
                "maxlength": rules.get("application_name_max_length"),
            }
        )
        self.fields["motivation"].widget.attrs.update(
            {
                "minlength": rules.get("application_motivation_min_length"),
                "maxlength": rules.get("application_motivation_max_length"),
            }
        )
        earliest, latest = birth_date_bounds(
            clock.today(),
            rules.get("min_volunteer_age"),
            rules.get("volunteer_max_age"),
        )
        self.fields["date_of_birth"].widget.attrs.update(
            {"min": earliest.isoformat(), "max": latest.isoformat()}
        )
        for name, field in self.fields.items():
            if name in {"website", "render_token"}:
                continue
            identifiers = [f"id_{name}_hint"]
            if self.is_bound and name in self.errors:
                identifiers.append(f"id_{name}_errors")
                field.widget.attrs["aria-invalid"] = "true"
            field.widget.attrs["aria-describedby"] = " ".join(identifiers)

    def clean_full_name(self):
        name = " ".join(self.cleaned_data["full_name"].split())
        # BR-040: explicit Unicode letter/mark categories, no regex dependency.
        valid_characters = all(
            unicodedata.category(char)[0] in {"L", "M"} or char in " .'-"
            for char in name
        )
        if (
            not rules.get("application_name_min_length")
            <= len(name)
            <= rules.get("application_name_max_length")
            or not valid_characters
        ):
            raise forms.ValidationError(
                _(
                    "Enter a name of 3–100 characters using letters, spaces, periods, "
                    "apostrophes or hyphens."
                )
            )
        return name

    def clean_email(self):
        return self.cleaned_data["email"].lower()

    def clean_phone(self):
        phone = re.sub(r"[\s-]", "", self.cleaned_data["phone"])
        if phone.startswith("03"):
            phone = "+92" + phone[1:]
        elif phone.startswith("923"):
            phone = "+" + phone
        if re.fullmatch(r"\+923[0-9]{9}", phone) is None:
            raise forms.ValidationError(_("Enter a valid Pakistani mobile number."))
        return phone

    def clean_interests(self):
        values = self.cleaned_data["interests"]
        if len(values) > rules.get("application_max_interests"):
            raise forms.ValidationError(_("Choose between one and five interests."))
        return list(dict.fromkeys(values))

    def clean_motivation(self):
        text = self.cleaned_data["motivation"].strip()
        if (
            not rules.get("application_motivation_min_length")
            <= len(text)
            <= rules.get("application_motivation_max_length")
        ):
            raise forms.ValidationError(_("Write between 20 and 1000 characters."))
        return text

    def clean(self):
        cleaned = super().clean()
        birth = cleaned.get("date_of_birth")
        if birth is not None:
            today = clock.today()
            age = age_on(birth, today)
            if birth > today or not rules.get("min_volunteer_age") <= age <= rules.get(
                "volunteer_max_age"
            ):
                self.add_error(
                    "date_of_birth",
                    _(
                        "Applicants must be between %(minimum)s and %(maximum)s "
                        "years old."
                    )
                    % {
                        "minimum": rules.get("min_volunteer_age"),
                        "maximum": rules.get("volunteer_max_age"),
                    },
                )
            elif age < rules.get("guardian_consent_age") and not cleaned.get(
                "guardian_consent"
            ):
                self.add_error(
                    "guardian_consent",
                    _("Parent or guardian consent is required if you are under 18."),
                )
        return cleaned
