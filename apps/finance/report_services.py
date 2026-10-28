"""Weekly report writes use explicit transactions and the existing audit chain."""

import hashlib
import json
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from apps import audit
from apps.accounts.permissions import require, scope_queryset
from apps.audit.services import canonical_json
from apps.branches.models import Branch, BranchStatus
from apps.core import clock, rules
from apps.core.exceptions import InvalidTransition
from apps.finance.models import ReportStatus, WeeklyReport, WeeklyReportLine
from apps.finance.report_forms import ReportNarrativeForm
from apps.finance.report_selectors import (
    report_aggregates,
    week_bounds,
    week_collections,
)

REPORT_TRANSITIONS = {
    (ReportStatus.DRAFT, "submit"): ReportStatus.SUBMITTED,
    (ReportStatus.SUBMITTED, "return"): ReportStatus.RETURNED,
    (ReportStatus.RETURNED, "resubmit"): ReportStatus.RESUBMITTED,
    (ReportStatus.RESUBMITTED, "return"): ReportStatus.RETURNED,
    (ReportStatus.SUBMITTED, "approve"): ReportStatus.APPROVED,
    (ReportStatus.RESUBMITTED, "approve"): ReportStatus.APPROVED,
}


def _locked_report(actor, report, permission):
    require(actor, permission)
    scoped = scope_queryset(actor, permission, WeeklyReport.objects.all())
    item = get_object_or_404(scoped, pk=report.pk)
    # Match collection writes and branch closure: branch first, report second.
    branch = Branch.objects.select_for_update(no_key=True).get(pk=item.branch_id)
    item = get_object_or_404(scoped.select_for_update(no_key=True), pk=item.pk)
    item.branch = branch
    return item


def _valid_narrative(data):
    form = ReportNarrativeForm(data)
    if not form.is_valid():
        raise ValidationError(form.errors.as_data())
    return form.cleaned_data


def save_narrative(actor, report, data):
    """Save registered fields in Draft/Returned without changing revision."""
    with transaction.atomic():
        item = _locked_report(actor, report, "report.edit_narrative")
        if item.status not in {ReportStatus.DRAFT, ReportStatus.RETURNED}:
            raise InvalidTransition(
                _("Narrative can only be edited in Draft or Returned reports.")
            )
        before = {"narrative": item.narrative}
        item.narrative = _valid_narrative(data)
        item.updated_at = clock.now()
        item.full_clean()
        item.save(update_fields=["narrative", "updated_at"])
        audit.record(
            actor,
            "report.narrative_updated",
            entity=item,
            branch_id=item.branch_id,
            before=before,
            after={"narrative": item.narrative},
        )
        return item


def transition(
    actor, report, action, *, expected_revision=None, comment="", narrative=None
):
    """Perform one guarded transition; approval and lock commit together. BR-085–089."""
    with transaction.atomic():
        item = _locked_report(actor, report, f"report.{action}")
        target = REPORT_TRANSITIONS.get((item.status, action))
        if target is None:
            raise InvalidTransition(
                _("This action is not available for the report's current status.")
            )
        before = {
            "status": item.status,
            "revision": item.revision,
            "snapshot": item.snapshot,
            "snapshot_hash": item.snapshot_hash,
        }
        current = clock.now()
        if action in {"submit", "resubmit"}:
            today = clock.today()
            if today <= item.week_end and (
                not rules.get("allow_submit_current_week") or today < item.week_start
            ):
                raise InvalidTransition(_("The reporting week has not ended yet."))
            item.narrative = _valid_narrative(
                item.narrative if narrative is None else narrative
            )
            item.revision += 1
            selected = list(
                week_collections(item.branch, item.week_start).select_for_update(
                    no_key=True
                )
            )
            snapshot = {
                **report_aggregates(item.branch, item.week_start),
                "narrative": item.narrative,
                "branch_id": item.branch_id,
                "week_start": item.week_start,
                "week_end": item.week_end,
                "revision": item.revision,
                "lines": [
                    {
                        "collection_id": entry.pk,
                        "reference": entry.reference,
                        "collection_date": entry.collection_date,
                        "method": entry.method,
                        "amount": entry.amount,
                    }
                    for entry in selected
                ],
            }
            item.snapshot = json.loads(canonical_json(snapshot))
            item.snapshot_hash = hashlib.sha256(
                canonical_json(item.snapshot).encode()
            ).hexdigest()
            WeeklyReportLine.objects.bulk_create(
                [
                    WeeklyReportLine(
                        report=item,
                        revision=item.revision,
                        collection=entry,
                        reference=entry.reference,
                        collection_date=entry.collection_date,
                        method=entry.method,
                        amount=entry.amount,
                    )
                    for entry in selected
                ]
            )
            item.submitted_by, item.submitted_at = actor, current
        else:
            if expected_revision != item.revision:
                raise InvalidTransition(
                    _("This report revision has changed. Reload before reviewing.")
                )
            comment = comment.strip()
            if action == "return" and not rules.get(
                "report_return_comment_min_length"
            ) <= len(comment) <= rules.get("report_return_comment_max_length"):
                raise ValidationError(
                    {
                        "comment": _(
                            "Give a return comment between %(minimum)s "
                            "and %(maximum)s characters."
                        )
                        % {
                            "minimum": rules.get("report_return_comment_min_length"),
                            "maximum": rules.get("report_return_comment_max_length"),
                        }
                    }
                )
            item.reviewed_by, item.reviewed_at, item.review_comment = (
                actor,
                current,
                comment,
            )
            if action == "approve":
                item.approved_by, item.approved_at = actor, current
        item.status, item.updated_at = target, current
        item.full_clean()
        item.save()
        event_action = {
            "submit": "report.submitted",
            "resubmit": "report.resubmitted",
            "return": "report.returned",
            "approve": "report.approved",
        }[action]
        audit.record(
            actor,
            event_action,
            entity=item,
            branch_id=item.branch_id,
            before=before,
            after={
                "status": item.status,
                "revision": item.revision,
                "snapshot": item.snapshot,
                "snapshot_hash": item.snapshot_hash,
            },
            metadata={"comment": comment} if action in {"return", "approve"} else {},
        )
        if action == "approve":
            item.status, item.locked_at = ReportStatus.LOCKED, current
            item.save(update_fields=["status", "locked_at", "updated_at"])
            audit.record(
                None,
                "report.locked",
                entity=item,
                branch_id=item.branch_id,
                before={"status": ReportStatus.APPROVED},
                after={"status": ReportStatus.LOCKED, "locked_at": item.locked_at},
                metadata={"approved_by_id": actor.pk},
            )
        return item


def ensure_drafts(branch, *, week_start=None):
    """Lazily create missing weeks once, with system audit events. BR-081, BR-082."""
    reports = []
    with transaction.atomic():
        branch = Branch.objects.select_for_update(no_key=True).get(pk=branch.pk)
        if branch.status != BranchStatus.ACTIVE or branch.opened_on is None:
            return reports
        week = week_bounds(branch.opened_on)[0]
        current = week_bounds(clock.today())[0]
        if week_start is not None:
            if (
                week_start != week_bounds(week_start)[0]
                or not week <= week_start <= current
            ):
                raise ValidationError(_("Choose a reporting week since opening."))
            week = current = week_start
        while week <= current:
            report, created = WeeklyReport.objects.get_or_create(
                branch=branch,
                week_start=week,
                defaults={
                    "week_end": week + timedelta(days=6),
                    "created_at": clock.now(),
                    "updated_at": clock.now(),
                },
            )
            if created:
                audit.record(
                    None,
                    "report.drafted",
                    entity=report,
                    branch_id=branch.pk,
                    after={
                        "status": report.status,
                        "week_start": report.week_start,
                        "week_end": report.week_end,
                        "revision": 0,
                    },
                )
            reports.append(report)
            week += timedelta(days=7)
    return reports
