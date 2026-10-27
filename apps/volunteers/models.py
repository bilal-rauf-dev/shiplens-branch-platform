"""Volunteer applications and the member records created by HR acceptance."""

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex, OpClass
from django.db import models
from django.db.models.functions import Length, Lower, Trim, Upper
from django.db.models.lookups import GreaterThanOrEqual, LessThanOrEqual
from django.utils.translation import gettext_lazy as _

from apps.core import clock


class ApplicationStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    ACCEPTED = "ACCEPTED", _("Accepted")
    DECLINED = "DECLINED", _("Declined")


class MemberStatus(models.TextChoices):
    ACTIVE = "ACTIVE", _("Active")
    INACTIVE = "INACTIVE", _("Inactive")
    LEFT = "LEFT", _("Left")


class VolunteerRole(models.Model):
    code = models.CharField(_("code"), max_length=30, unique=True)
    name_en = models.CharField(_("English name"), max_length=60)
    name_ur = models.CharField(_("Urdu name"), max_length=60)
    is_active = models.BooleanField(_("active"), default=True)
    sort_order = models.PositiveIntegerField(_("sort order"), default=0)

    class Meta:
        db_table = "volunteer_roles"

    def __str__(self):
        return self.name_en


class Team(models.Model):
    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.RESTRICT, related_name="teams"
    )
    name = models.CharField(_("name"), max_length=60)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        db_table = "teams"
        constraints = [
            models.UniqueConstraint(
                "branch", Lower("name"), name="teams_branch_name_unique"
            ),
            models.UniqueConstraint(
                fields=["id", "branch"], name="teams_id_branch_unique"
            ),
        ]

    def __str__(self):
        return self.name


class Application(models.Model):
    reference = models.CharField(_("reference"), max_length=16, unique=True)
    full_name = models.CharField(_("full name"), max_length=100)
    email = models.EmailField(_("email"), max_length=254, db_index=True)
    phone = models.CharField(_("phone"), max_length=16, db_index=True)
    date_of_birth = models.DateField(_("date of birth"))
    guardian_consent = models.BooleanField(_("guardian consent"), default=False)
    preferred_branch = models.ForeignKey(
        "branches.Branch", on_delete=models.RESTRICT, related_name="applications"
    )
    interests = ArrayField(models.CharField(max_length=40), verbose_name=_("interests"))
    availability = ArrayField(
        models.CharField(max_length=40), verbose_name=_("availability")
    )
    motivation = models.TextField(_("motivation"), max_length=1000)
    preferred_language = models.CharField(
        _("preferred language"), max_length=5, choices=settings.LANGUAGES
    )
    consent_at = models.DateTimeField(_("consent at"))
    status = models.CharField(
        _("status"),
        max_length=10,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING,
    )
    possible_duplicate = models.BooleanField(_("possible duplicate"), default=False)
    duplicate_of_application = models.ForeignKey(
        "self",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="possible_duplicates",
    )
    duplicate_of_member = models.ForeignKey(
        "Member",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="possible_duplicate_applications",
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="decided_applications",
    )
    decided_at = models.DateTimeField(_("decided at"), null=True, blank=True)
    decision_note = models.CharField(_("decision note"), max_length=500, blank=True)
    member = models.OneToOneField(
        "Member",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="accepted_application",
    )
    ip_hash = models.CharField(_("IP hash"), max_length=64)
    created_at = models.DateTimeField(_("created at"), default=clock.now)
    updated_at = models.DateTimeField(_("updated at"), default=clock.now)

    class Meta:
        db_table = "applications"
        indexes = [
            models.Index(
                fields=["preferred_branch", "status", "-created_at"],
                name="applications_branch_status",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=ApplicationStatus.values),
                name="applications_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(preferred_language__in=["en", "ur"]),
                name="applications_language_valid",
            ),
            models.CheckConstraint(
                condition=GreaterThanOrEqual(Length("motivation"), 20)
                & LessThanOrEqual(Length("motivation"), 1000),
                name="applications_motivation_length",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status=ApplicationStatus.ACCEPTED, member__isnull=False)
                    | (
                        ~models.Q(status=ApplicationStatus.ACCEPTED)
                        & models.Q(member__isnull=True)
                    )
                ),
                name="applications_accepted_member",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(status=ApplicationStatus.DECLINED)
                    | GreaterThanOrEqual(Length(Trim("decision_note")), 5)
                ),
                name="applications_decline_reason",
            ),
        ]

    def __str__(self):
        return self.reference


class Member(models.Model):
    member_id = models.CharField(_("member ID"), max_length=16, unique=True)
    application = models.OneToOneField(
        Application,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="created_member",
    )
    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.RESTRICT, related_name="members"
    )
    team = models.ForeignKey(
        Team, on_delete=models.RESTRICT, null=True, blank=True, related_name="members"
    )
    volunteer_role = models.ForeignKey(
        VolunteerRole, on_delete=models.RESTRICT, related_name="members"
    )
    full_name = models.CharField(_("full name"), max_length=100)
    email = models.EmailField(_("email"), max_length=254)
    phone = models.CharField(_("phone"), max_length=16)
    status = models.CharField(
        _("status"),
        max_length=10,
        choices=MemberStatus.choices,
        default=MemberStatus.ACTIVE,
    )
    joined_on = models.DateField(_("joined on"))
    left_on = models.DateField(_("left on"), null=True, blank=True)
    notes = models.CharField(_("notes"), max_length=1000, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="created_members",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="updated_members",
    )
    created_at = models.DateTimeField(_("created at"), default=clock.now)
    updated_at = models.DateTimeField(_("updated at"), default=clock.now)

    class Meta:
        db_table = "members"
        indexes = [
            models.Index(fields=["branch", "status"], name="members_branch_status"),
            models.Index(fields=["branch", "joined_on"], name="members_branch_joined"),
            models.Index(fields=["joined_on"], name="members_joined"),
            models.Index(fields=["status"], name="members_status"),
            models.Index(fields=["created_at"], name="members_created"),
            models.Index(Lower("full_name"), name="members_name_lower"),
            # Django's PostgreSQL icontains queries UPPER(field), not the bare column.
            GinIndex(
                OpClass(Upper("full_name"), name="gin_trgm_ops"),
                name="members_name_trgm",
            ),
            GinIndex(
                OpClass(Upper("email"), name="gin_trgm_ops"), name="members_email_trgm"
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                condition=~models.Q(status=MemberStatus.LEFT),
                name="members_current_email_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=MemberStatus.values),
                name="members_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status=MemberStatus.LEFT, left_on__isnull=False)
                    | (
                        ~models.Q(status=MemberStatus.LEFT)
                        & models.Q(left_on__isnull=True)
                    )
                ),
                name="members_left_date_required",
            ),
            models.CheckConstraint(
                condition=models.Q(left_on__isnull=True)
                | models.Q(left_on__gte=models.F("joined_on")),
                name="members_dates_valid",
            ),
        ]

    def __str__(self):
        return self.member_id
