from datetime import date

from django.utils.formats import date_format
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from apps.accounts.permissions import assigned_branch_ids
from apps.core import clock
from apps.core.views import PermissionRequiredMixin
from apps.dashboard import kpis, selectors
from apps.dashboard.forms import PeriodForm


class DashboardView(PermissionRequiredMixin, TemplateView):
    template_name = "dashboard/financial.html"
    required_action = "dashboard.head_office"
    head_office = True

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(
            context, status=400 if context["period_invalid"] else 200
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        as_of = clock.now()
        form = PeriodForm(self.request.GET or None)
        invalid = form.is_bound and not form.is_valid()
        if form.is_bound and not invalid:
            selected = form.cleaned_data["period"]
            period = selected.year, selected.month
        else:
            period = kpis.default_period(as_of)
            if not form.is_bound:
                form = PeriodForm(initial={"period": date(*period, 1)})
        current = as_of.year, as_of.month
        context.update(
            form=form,
            period=period,
            period_invalid=invalid,
            as_of=as_of,
            period_label=date_format(date(*period, 1), "F Y"),
            latest_month=not self.request.GET and period != current,
            head_office=self.head_office,
        )
        branch_ids = (
            None if self.head_office else list(assigned_branch_ids(self.request.user))
        )
        context.update(
            selectors.dashboard_data(
                period, as_of, branch_ids, head_office=self.head_office
            )
        )
        context["chart_labels"] = {
            "collected": _("Collected"),
            "approved": _("Approved"),
            "members": _("New members"),
        }
        return context


class BranchDashboardView(DashboardView):
    required_action = "dashboard.branch"
    head_office = False


class HRDashboardView(DashboardView):
    template_name = "dashboard/hr.html"
    required_action = "dashboard.hr"
    head_office = False

    def get_context_data(self, **kwargs):
        # HR sees the current pipeline, not financial aggregates or chart data.
        as_of = clock.now()
        form = PeriodForm(self.request.GET or None)
        invalid = form.is_bound and not form.is_valid()
        selected = (
            form.cleaned_data["period"]
            if form.is_bound and not invalid
            else date(*kpis.default_period(as_of), 1)
        )
        if not form.is_bound:
            form = PeriodForm(initial={"period": selected})
        period = selected.year, selected.month
        return {
            "form": form,
            "period": period,
            "period_invalid": invalid,
            "as_of": as_of,
            "period_label": date_format(selected, "F Y"),
            "latest_month": not self.request.GET
            and period != (as_of.year, as_of.month),
            **selectors.hr_data(
                period, as_of, list(assigned_branch_ids(self.request.user))
            ),
        }
