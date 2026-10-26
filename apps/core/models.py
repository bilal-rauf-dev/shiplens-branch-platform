from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core import clock


class SystemSetting(models.Model):
    key = models.CharField(_("key"), max_length=50, primary_key=True)
    value = models.JSONField(_("value"))
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="updated_settings",
        verbose_name=_("updated by"),
    )
    updated_at = models.DateTimeField(_("updated at"), default=clock.now)

    class Meta:
        db_table = "system_settings"
        verbose_name = _("system setting")
        verbose_name_plural = _("system settings")

    def __str__(self):
        return self.key


class IdSequence(models.Model):
    key = models.CharField(_("key"), max_length=40, primary_key=True)
    last_value = models.PositiveIntegerField(_("last value"), default=0)
    updated_at = models.DateTimeField(_("updated at"), default=clock.now)

    class Meta:
        db_table = "id_sequences"
        verbose_name = _("ID sequence")
        verbose_name_plural = _("ID sequences")

    def __str__(self):
        return self.key
