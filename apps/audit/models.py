"""Security and business history, protected from mutation by database triggers."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core import clock


class AuditLog(models.Model):
    occurred_at = models.DateTimeField(_("occurred at"), default=clock.now)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        verbose_name=_("actor"),
    )
    actor_label = models.CharField(_("actor label"), max_length=254)
    actor_role = models.CharField(_("actor role"), max_length=20, blank=True)
    action = models.CharField(_("action"), max_length=60)
    entity_type = models.CharField(_("entity type"), max_length=40, blank=True)
    entity_id = models.PositiveBigIntegerField(_("entity ID"), null=True, blank=True)
    entity_label = models.CharField(_("entity label"), max_length=120, blank=True)
    branch_id = models.PositiveBigIntegerField(_("branch ID"), null=True, blank=True)
    before = models.JSONField(_("before"), default=dict, blank=True)
    after = models.JSONField(_("after"), default=dict, blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)
    ip = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    user_agent = models.CharField(_("user agent"), max_length=200, blank=True)
    request_id = models.UUIDField(_("request ID"), null=True, blank=True)
    prev_hash = models.CharField(_("previous hash"), max_length=64)
    hash = models.CharField(_("hash"), max_length=64)

    class Meta:
        db_table = "audit_log"
        verbose_name = _("audit event")
        verbose_name_plural = _("audit events")
        indexes = [
            models.Index(
                fields=["entity_type", "entity_id", "occurred_at"],
                name="audit_entity_time",
            ),
            models.Index(fields=["-occurred_at"], name="audit_time_desc"),
            models.Index(fields=["action"], name="audit_action"),
            models.Index(fields=["branch_id", "occurred_at"], name="audit_branch_time"),
        ]

    def __str__(self):
        return f"{self.pk}: {self.action}"
