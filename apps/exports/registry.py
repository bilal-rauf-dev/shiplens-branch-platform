"""Stable column order and explicit getters for the planning/13 catalogue."""

from dataclasses import dataclass
from decimal import Decimal

from django.utils.translation import gettext_lazy as _

from apps.audit.services import canonical_json
from apps.core import clock
from apps.exports import selectors


@dataclass(frozen=True)
class Export:
    action: str
    rows_fn: object
    columns: list
    form_fn: object


def timestamp(value):
    return value.astimezone(clock.KARACHI).isoformat() if value else ""


EXPORTS = {
    "collections": Export(
        "collection.export_csv",
        selectors.collections,
        [
            (_("Reference"), lambda r: r.reference),
            (_("Branch code"), lambda r: r.branch.code),
            (_("Collection date"), lambda r: r.collection_date),
            (_("Method"), lambda r: r.method),
            (_("Amount"), lambda r: r.amount),
            (_("Receipt number"), lambda r: r.receipt_no),
            (_("Source note"), lambda r: r.source_note),
            (_("Status"), lambda r: str(r.state)),
            (
                _("Transfer reference"),
                lambda r: r.transfer.reference if r.transfer else "",
            ),
            (_("Created by"), lambda r: r.created_by.email),
            (_("Created at (PKT)"), lambda r: timestamp(r.created_at)),
        ],
        selectors.collection_form,
    ),
    "unsent": Export(
        "unsent.export_csv",
        selectors.unsent,
        [
            (_("Branch code"), lambda r: r["branch_code"]),
            (_("Reference"), lambda r: r["reference"]),
            (_("Collection date"), lambda r: r["date"]),
            (_("Method"), lambda r: r["method"]),
            (_("Amount"), lambda r: r["amount"]),
            (_("Age (days)"), lambda r: r["age"]),
            (_("Locked"), lambda r: r["locked"]),
            (_("Week report"), lambda r: r["report_status"]),
        ],
        selectors.period_form,
    ),
    "reports": Export(
        "report.export_csv",
        selectors.reports,
        [
            (_("Branch code"), lambda r: r.branch.code),
            (_("Week start"), lambda r: r.week_start),
            (_("Week end"), lambda r: r.week_end),
            (_("Status"), lambda r: r.status),
            (_("Revision"), lambda r: r.revision),
            (
                _("Total amount"),
                lambda r: Decimal(selectors.report_figures(r)["total_amount"]),
            ),
            (_("Entry count"), lambda r: selectors.report_figures(r)["entry_count"]),
            (_("Submitted at (PKT)"), lambda r: timestamp(r.submitted_at)),
            (_("Approved at (PKT)"), lambda r: timestamp(r.approved_at)),
        ],
        selectors.report_form,
    ),
    "summary": Export(
        "summary.export_csv",
        selectors.summary,
        [
            (_("Branch code"), lambda r: r["branch_code"]),
            (_("Status"), lambda r: r["branch_status"]),
            (_("Collected"), lambda r: r["collected"]),
            (_("Collection count"), lambda r: r["collected_count"]),
            (_("Approved"), lambda r: r["approved"]),
            (_("Unsent"), lambda r: r["unsent"]),
            (_("Unsent count"), lambda r: r["unsent_count"]),
            (_("Oldest age (days)"), lambda r: r["oldest_age"]),
            (
                _("Latest report"),
                lambda r: r["latest_report"]["status"] if r["latest_report"] else "",
            ),
        ],
        selectors.period_form,
    ),
    "members": Export(
        "member.export_csv",
        selectors.members,
        [
            (_("Member ID"), lambda r: r.member_id),
            (_("Full name"), lambda r: r.full_name),
            (_("Branch code"), lambda r: r.branch.code),
            (_("Team"), lambda r: r.team.name if r.team else ""),
            (_("Volunteer role"), lambda r: r.volunteer_role.code),
            (_("Status"), lambda r: r.status),
            (_("Joined on"), lambda r: r.joined_on),
            (_("Left on"), lambda r: r.left_on),
            (_("Email"), lambda r: r.email),
            (_("Phone"), lambda r: r.phone),
        ],
        selectors.member_form,
    ),
    "audit": Export(
        "audit.export_csv",
        selectors.events,
        [
            (_("Occurred at (PKT)"), lambda r: timestamp(r.occurred_at)),
            (_("Actor"), lambda r: r.actor_label),
            (_("Actor role"), lambda r: r.actor_role),
            (_("Action"), lambda r: r.action),
            (_("Entity type"), lambda r: r.entity_type),
            (_("Entity label"), lambda r: r.entity_label),
            (_("Branch code"), lambda r: r.export_branch_code),
            (
                _("Changes (JSON)"),
                lambda r: canonical_json({"before": r.before, "after": r.after}),
            ),
            (_("IP address"), lambda r: r.ip),
            (_("Request ID"), lambda r: r.request_id),
        ],
        selectors.audit_form,
    ),
}
