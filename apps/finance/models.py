"""Offline collection records; entry state is derived rather than stored."""

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models.functions import Length, Trim
from django.db.models.lookups import GreaterThanOrEqual
from django.utils.translation import gettext_lazy as _

from apps.core import clock, rules


class CollectionMethod(models.TextChoices):
    CASH = "CASH", _("Cash")
    CHEQUE = "CHEQUE", _("Cheque")
    BANK_DEPOSIT = "BANK_DEPOSIT", _("Bank deposit")


class CollectionState(models.TextChoices):
    OPEN = "OPEN", _("Open")
    LOCKED = "LOCKED", _("Locked")
    SENT = "SENT", _("Sent")
    VOIDED = "VOIDED", _("Voided")


class ReportStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    SUBMITTED = "SUBMITTED", _("Submitted")
    RETURNED = "RETURNED", _("Returned")
    RESUBMITTED = "RESUBMITTED", _("Resubmitted")
    APPROVED = "APPROVED", _("Approved")
    LOCKED = "LOCKED", _("Locked")


class WeeklyReport(models.Model):
    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.RESTRICT, related_name="weekly_reports"
    )
    week_start = models.DateField(_("week start"), db_index=True)
    week_end = models.DateField(_("week end"))
    status = models.CharField(
        _("status"),
        max_length=12,
        choices=ReportStatus.choices,
        default=ReportStatus.DRAFT,
        db_index=True,
    )
    revision = models.IntegerField(_("revision"), default=0)
    narrative = models.JSONField(_("narrative"), default=dict, blank=True)
    snapshot = models.JSONField(_("snapshot"), default=dict, blank=True)
    snapshot_hash = models.CharField(_("snapshot hash"), max_length=64, blank=True)
    submitted_at = models.DateTimeField(_("submitted at"), null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="submitted_reports",
    )
    reviewed_at = models.DateTimeField(_("reviewed at"), null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="reviewed_reports",
    )
    review_comment = models.CharField(_("review comment"), max_length=1000, blank=True)
    approved_at = models.DateTimeField(_("approved at"), null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="approved_reports",
    )
    locked_at = models.DateTimeField(_("locked at"), null=True, blank=True)
    created_at = models.DateTimeField(_("created at"), default=clock.now)
    updated_at = models.DateTimeField(_("updated at"), default=clock.now)

    class Meta:
        db_table = "weekly_reports"
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "week_start"], name="reports_branch_week_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(week_start__iso_week_day=1),
                name="reports_start_monday",
            ),
            models.CheckConstraint(
                condition=models.Q(week_end=models.F("week_start") + timedelta(days=6)),
                name="reports_end_sunday",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=ReportStatus.values),
                name="reports_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(revision__gte=0), name="reports_revision_valid"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status=ReportStatus.LOCKED, locked_at__isnull=False)
                    | (
                        ~models.Q(status=ReportStatus.LOCKED)
                        & models.Q(locked_at__isnull=True)
                    )
                ),
                name="reports_locked_timestamp",
            ),
        ]

    def __str__(self):
        return f"{self.branch.code} · {self.week_start.isoformat()}"


class WeeklyReportLine(models.Model):
    report = models.ForeignKey(
        WeeklyReport, on_delete=models.RESTRICT, related_name="lines"
    )
    revision = models.PositiveIntegerField(_("revision"))
    collection = models.ForeignKey(
        "Collection", on_delete=models.RESTRICT, related_name="report_lines"
    )
    reference = models.CharField(_("reference"), max_length=40)
    collection_date = models.DateField(_("collection date"))
    method = models.CharField(
        _("method"), max_length=14, choices=CollectionMethod.choices
    )
    amount = models.DecimalField(_("amount"), max_digits=12, decimal_places=2)

    class Meta:
        db_table = "weekly_report_lines"
        constraints = [
            models.UniqueConstraint(
                fields=["report", "revision", "collection"],
                name="report_lines_revision_unique",
            )
        ]

    def __str__(self):
        return f"{self.reference} · {self.revision}"


class EntryType(models.TextChoices):
    COLLECTION = "COLLECTION", _("Collection")
    ADJUSTMENT = "ADJUSTMENT", _("Adjustment")


class Transfer(models.Model):
    # The table is needed by Collection's FK; transfer operations arrive in P6 step 3.
    reference = models.CharField(_("reference"), max_length=40, unique=True)
    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.RESTRICT, related_name="transfers"
    )
    transfer_date = models.DateField(_("transfer date"))
    bank_reference = models.CharField(_("bank reference"), max_length=50)
    total_amount = models.DecimalField(
        _("total amount"), max_digits=12, decimal_places=2
    )
    note = models.TextField(_("note"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="created_transfers",
    )
    created_at = models.DateTimeField(_("created at"), default=clock.now)

    class Meta:
        db_table = "transfers"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_amount__gt=0), name="transfers_amount_positive"
            )
        ]

    def __str__(self):
        return self.reference


class Collection(models.Model):
    reference = models.CharField(_("reference"), max_length=40, unique=True)
    branch = models.ForeignKey(
        "branches.Branch", on_delete=models.RESTRICT, related_name="collections"
    )
    entry_type = models.CharField(
        _("entry type"),
        max_length=10,
        choices=EntryType.choices,
        default=EntryType.COLLECTION,
    )
    adjusts_collection = models.ForeignKey(
        "self",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="adjustments",
    )
    collection_date = models.DateField(_("collection date"))
    amount = models.DecimalField(_("amount"), max_digits=12, decimal_places=2)
    method = models.CharField(
        _("method"), max_length=14, choices=CollectionMethod.choices
    )
    receipt_no = models.CharField(_("receipt number"), max_length=30)
    collected_by_member = models.ForeignKey(
        "volunteers.Member",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="collections",
    )
    source_note = models.CharField(_("source note"), max_length=200, blank=True)
    transfer = models.ForeignKey(
        Transfer,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="collections",
    )
    voided_at = models.DateTimeField(_("voided at"), null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="voided_collections",
    )
    void_reason = models.CharField(_("void reason"), max_length=300, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="created_collections",
    )
    created_at = models.DateTimeField(_("created at"), default=clock.now)
    updated_at = models.DateTimeField(_("updated at"), default=clock.now)

    class Meta:
        db_table = "collections"
        indexes = [
            models.Index(
                fields=["branch", "collection_date"], name="collections_branch_date"
            ),
            models.Index(
                fields=["branch", "collection_date"],
                condition=models.Q(transfer__isnull=True, voided_at__isnull=True),
                name="collections_unsent",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "receipt_no"], name="collections_branch_receipt"
            ),
            models.CheckConstraint(
                condition=models.Q(entry_type__in=EntryType.values),
                name="collections_entry_type_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(entry_type=EntryType.ADJUSTMENT) | models.Q(amount__gt=0)
                )
                & ~models.Q(amount=0),
                name="collections_amount_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(method__in=CollectionMethod.values),
                name="collections_method_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        entry_type=EntryType.ADJUSTMENT,
                        adjusts_collection__isnull=False,
                    )
                    | models.Q(
                        entry_type=EntryType.COLLECTION, adjusts_collection__isnull=True
                    )
                ),
                name="collections_adjustment_link",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        voided_at__isnull=True, voided_by__isnull=True, void_reason=""
                    )
                    | (
                        models.Q(voided_at__isnull=False, voided_by__isnull=False)
                        & GreaterThanOrEqual(Length(Trim("void_reason")), 1)
                    )
                ),
                name="collections_void_all_or_none",
            ),
        ]

    def __str__(self):
        return self.reference

    def save(self, *args, **kwargs):
        # Services own writes; this guard also stops accidental direct model saves.
        # Marking sent updates only transfer/updated_at and is allowed after locking.
        from apps.finance.services import EDITABLE_FIELDS, assert_editable

        fields = kwargs.get("update_fields")
        guarded = {
            *EDITABLE_FIELDS,
            "collected_by_member",
            "voided_at",
            "voided_by",
            "void_reason",
            "branch",
            "branch_id",
        }
        if (
            self.pk
            and not kwargs.get("force_insert")
            and (fields is None or guarded.intersection(fields))
        ):
            previous = Collection.objects.filter(pk=self.pk).first()
            if previous is not None:
                assert_editable(previous)
        return super().save(*args, **kwargs)

    @property
    def lock_at(self):
        return self.created_at + timedelta(days=rules.get("collection_lock_days"))

    @property
    def is_locked(self):
        return clock.now() >= self.lock_at

    @property
    def state(self):
        if self.voided_at is not None:
            return CollectionState.VOIDED
        if self.transfer_id is not None:
            return CollectionState.SENT
        return CollectionState.LOCKED if self.is_locked else CollectionState.OPEN
