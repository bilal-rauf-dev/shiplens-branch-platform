"""The branch identity needed for assignments; P3 adds branch operations."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class BranchStatus(models.TextChoices):
    FORMING = "FORMING", _("Forming")
    ACTIVE = "ACTIVE", _("Active")
    PAUSED = "PAUSED", _("Paused")
    CLOSED = "CLOSED", _("Closed")


class Branch(models.Model):
    code = models.CharField(_("code"), max_length=16, unique=True)
    name_en = models.CharField(_("English name"), max_length=100)
    status = models.CharField(
        _("status"),
        max_length=10,
        choices=BranchStatus.choices,
        default=BranchStatus.FORMING,
    )

    class Meta:
        db_table = "branches"
        verbose_name = _("branch")
        verbose_name_plural = _("branches")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=BranchStatus.values),
                name="branches_status_valid",
            )
        ]

    def __str__(self):
        return self.name_en
