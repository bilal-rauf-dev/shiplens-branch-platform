"""Cities and bilingual branch records with database-backed identity constraints."""

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from apps.core import clock


class City(models.Model):
    code = models.CharField(
        _("code"),
        max_length=3,
        unique=True,
        validators=[RegexValidator(r"\A[A-Z]{3}\Z", _("Use three uppercase letters."))],
    )
    name_en = models.CharField(_("English name"), max_length=60)
    name_ur = models.CharField(_("Urdu name"), max_length=60)
    created_at = models.DateTimeField(_("created at"), default=clock.now)
    updated_at = models.DateTimeField(_("updated at"), default=clock.now)

    class Meta:
        db_table = "cities"
        verbose_name = _("city")
        verbose_name_plural = _("cities")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(code__regex=r"^[A-Z]{3}$"),
                name="cities_code_valid",
            )
        ]

    def __str__(self):
        return self.name_en


class BranchStatus(models.TextChoices):
    FORMING = "FORMING", _("Forming")
    ACTIVE = "ACTIVE", _("Active")
    PAUSED = "PAUSED", _("Paused")
    CLOSED = "CLOSED", _("Closed")


class Branch(models.Model):
    code = models.CharField(_("code"), max_length=16, unique=True)
    city = models.ForeignKey(
        City,
        on_delete=models.RESTRICT,
        related_name="branches",
        verbose_name=_("city"),
    )
    name_en = models.CharField(_("English name"), max_length=100)
    name_ur = models.CharField(_("Urdu name"), max_length=100)
    address_en = models.CharField(_("English address"), max_length=250, blank=True)
    address_ur = models.CharField(_("Urdu address"), max_length=250, blank=True)
    phone = models.CharField(
        _("phone"),
        max_length=16,
        blank=True,
        validators=[
            RegexValidator(
                r"\A\+[1-9][0-9]{1,14}\Z",
                _("Use an E.164 phone number, such as +922112345678."),
            )
        ],
    )
    email = models.EmailField(_("email address"), max_length=254, blank=True)
    status = models.CharField(
        _("status"),
        max_length=10,
        choices=BranchStatus.choices,
        default=BranchStatus.FORMING,
    )
    status_reason = models.CharField(_("status reason"), max_length=300, blank=True)
    opened_on = models.DateField(_("opened on"), null=True, blank=True)
    closed_on = models.DateField(_("closed on"), null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="created_branches",
        verbose_name=_("created by"),
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="updated_branches",
        verbose_name=_("updated by"),
    )
    created_at = models.DateTimeField(_("created at"), default=clock.now)
    updated_at = models.DateTimeField(_("updated at"), default=clock.now)

    class Meta:
        db_table = "branches"
        verbose_name = _("branch")
        verbose_name_plural = _("branches")
        indexes = [models.Index(fields=["status"], name="branches_status")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=BranchStatus.values),
                name="branches_status_valid",
            ),
            models.UniqueConstraint(
                "city", Lower("name_en"), name="branches_city_name_unique"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(closed_on__isnull=True)
                    | models.Q(opened_on__isnull=True)
                    | models.Q(closed_on__gte=models.F("opened_on"))
                ),
                name="branches_dates_valid",
            ),
        ]

    def __str__(self):
        return self.name_en
