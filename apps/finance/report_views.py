from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from apps.accounts.models import Role
from apps.accounts.permissions import can, require, scope_queryset
from apps.core.exceptions import InvalidTransition
from apps.core.views import PermissionRequiredMixin
from apps.finance import report_selectors as selectors
from apps.finance import report_services as services
from apps.finance.models import ReportStatus
from apps.finance.report_forms import (
    ReportFilterForm,
    ReportNarrativeForm,
    ReportReviewForm,
)
from apps.finance.views import add_errors


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class ReportListView(PermissionRequiredMixin, ListView):
    required_action = "report.list"
    queryset = selectors.reports()
    template_name = "finance/report_list.html"
    context_object_name = "reports"
    paginate_by = 25
    queue = False

    def get_queryset(self):
        if self.request.user.role == Role.BRANCH_LEAD:
            for branch in selectors.draft_branches(self.request.user).iterator():
                services.ensure_drafts(branch)
        self.filter_form = ReportFilterForm(self.request.GET, user=self.request.user)
        queryset = super().get_queryset()
        return (
            selectors.filter_reports(queryset, self.filter_form.cleaned_data)
            if self.filter_form.is_valid()
            else queryset.none()
        )

    def get_context_data(self, **kwargs):
        params = self.request.GET.copy()
        params.pop("page", None)
        return {
            **super().get_context_data(**kwargs),
            "filter_form": self.filter_form,
            "filter_query": params.urlencode(),
            "queue": self.queue,
        }


class ReportReviewQueueView(ReportListView):
    # Only users who can approve reports have a review queue; SA reads the list.
    required_action = "report.approve"
    queue = True

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(status__in=[ReportStatus.SUBMITTED, ReportStatus.RESUBMITTED])
            .order_by("submitted_at", "pk")
        )


def detail_context(request, report):
    editable = report.status in {ReportStatus.DRAFT, ReportStatus.RETURNED}
    reviewable = report.status in {ReportStatus.SUBMITTED, ReportStatus.RESUBMITTED}
    return {
        "report": report,
        **selectors.detail_data(request.user, report),
        "can_edit": editable and can(request.user, "report.edit_narrative", report),
        "can_review": reviewable and can(request.user, "report.approve", report),
        "narrative_form": ReportNarrativeForm(initial=report.narrative),
        "review_form": ReportReviewForm(initial={"expected_revision": report.revision}),
        "submit_route": "report-submit"
        if report.status == ReportStatus.DRAFT
        else "report-resubmit",
    }


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class ReportDetailView(PermissionRequiredMixin, DetailView):
    required_action = "report.view"
    queryset = selectors.reports()
    template_name = "finance/report_detail.html"
    context_object_name = "report"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            **detail_context(self.request, self.object),
        }


def _report(request, pk, action):
    require(request.user, action)
    return get_object_or_404(
        scope_queryset(request.user, action, selectors.reports()), pk=pk
    )


def _error(request, pk, form, key, status):
    report = _report(request, pk, "report.view")
    context = detail_context(request, report)
    context[key] = form
    context["error_messages"] = [
        message for errors in form.errors.values() for message in errors
    ]
    return render(request, "finance/report_detail.html", context, status=status)


def _narrative_action(request, pk, action):
    permission = "report.edit_narrative" if action == "save" else f"report.{action}"
    report = _report(request, pk, permission)
    form = ReportNarrativeForm(request.POST)
    if not form.is_valid():
        return _error(request, pk, form, "narrative_form", 400)
    try:
        if action == "save":
            services.save_narrative(request.user, report, form.cleaned_data)
        else:
            services.transition(
                request.user, report, action, narrative=form.cleaned_data
            )
    except ValidationError as error:
        add_errors(form, error)
        return _error(request, pk, form, "narrative_form", 400)
    except InvalidTransition as error:
        form.add_error(None, str(error))
        return _error(request, pk, form, "narrative_form", 409)
    messages.success(
        request,
        _("Report saved.") if action == "save" else _("Report submitted for review."),
    )
    return redirect("report-detail", pk=pk)


def _review_action(request, pk, action):
    report = _report(request, pk, f"report.{action}")
    form = ReportReviewForm(request.POST)
    if not form.is_valid():
        return _error(request, pk, form, "review_form", 400)
    try:
        services.transition(request.user, report, action, **form.cleaned_data)
    except ValidationError as error:
        add_errors(form, error)
        return _error(request, pk, form, "review_form", 400)
    except InvalidTransition as error:
        form.add_error(None, str(error))
        return _error(request, pk, form, "review_form", 409)
    messages.success(
        request,
        _("Report returned to the branch.")
        if action == "return"
        else _("Report approved and locked."),
    )
    return redirect("report-detail", pk=pk)


@cache_control(no_store=True, private=True)
@require_POST
def save(request, pk):
    return _narrative_action(request, pk, "save")


@cache_control(no_store=True, private=True)
@require_POST
def submit(request, pk):
    return _narrative_action(request, pk, "submit")


@cache_control(no_store=True, private=True)
@require_POST
def resubmit(request, pk):
    return _narrative_action(request, pk, "resubmit")


@cache_control(no_store=True, private=True)
@require_POST
def return_report(request, pk):
    return _review_action(request, pk, "return")


@cache_control(no_store=True, private=True)
@require_POST
def approve(request, pk):
    return _review_action(request, pk, "approve")
