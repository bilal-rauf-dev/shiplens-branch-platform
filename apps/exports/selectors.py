"""Export adapters reuse list forms and selectors, never their filtering logic."""

from datetime import date

from django.db.models import Max, OuterRef, Subquery

from apps.accounts.permissions import assigned_branch_ids, scope_queryset
from apps.audit import selectors as audit_selectors
from apps.audit.forms import AuditFilterForm
from apps.branches.models import Branch
from apps.core import clock
from apps.dashboard import kpis
from apps.dashboard.forms import PeriodForm
from apps.finance import report_selectors
from apps.finance import selectors as finance_selectors
from apps.finance.forms import CollectionFilterForm
from apps.finance.report_forms import ReportFilterForm
from apps.volunteers import selectors as member_selectors
from apps.volunteers.forms import MemberFilterForm
from apps.volunteers.models import MemberStatus


def collection_form(user, params):
    return CollectionFilterForm(params)


def report_form(user, params):
    return ReportFilterForm(params, user=user)


def member_form(user, params):
    params = params.copy()
    params.setdefault("status", MemberStatus.ACTIVE)
    return MemberFilterForm(params, user=user)


def audit_form(user, params):
    return AuditFilterForm(params, user=user)


def period_form(user, params):
    params = params.copy()
    # Match the dashboard's latest-populated-month default; lang/page aren't filters.
    if not params.get("period"):
        params["period"] = date(*kpis.default_period(clock.now()), 1).strftime("%Y-%m")
    return PeriodForm(params)


def collections(user, params):
    return finance_selectors.search_collections(user, params)


def reports(user, params):
    return report_selectors.filter_reports(
        scope_queryset(user, "report.list", report_selectors.reports()), params
    )


def members(user, params):
    return member_selectors.search_members(user, params)


def events(user, params):
    rows = audit_selectors.search_events(user, params)
    # The export's own audit entry must not enter its subsequently streamed rows.
    last_id = rows.aggregate(last_id=Max("pk"))["last_id"]
    rows = rows.filter(pk__lte=last_id) if last_id else rows.none()
    return rows.annotate(
        export_branch_code=Subquery(
            Branch.objects.filter(pk=OuterRef("branch_id")).values("code")[:1]
        )
    )


def branch_ids(user):
    return (
        list(assigned_branch_ids(user))
        if user.role in {"BRANCH_LEAD", "HR_LEAD"}
        else None
    )


def unsent(user, params):
    selected = params["period"]
    return kpis.l1((selected.year, selected.month), clock.now(), branch_ids(user))


def summary(user, params):
    selected = params["period"]
    return kpis.l2((selected.year, selected.month), clock.now())


def report_figures(report):
    if report.status in {"DRAFT", "RETURNED"}:
        return report_selectors.report_aggregates(report.branch, report.week_start)
    return report.snapshot
