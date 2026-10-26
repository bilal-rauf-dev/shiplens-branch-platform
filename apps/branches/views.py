from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, FormView, ListView

from apps.accounts.permissions import can, require, scope_queryset
from apps.branches import selectors, services
from apps.branches.forms import (
    BranchCreateForm,
    BranchEditForm,
    BranchFilterForm,
    CityCreateForm,
    CityEditForm,
)
from apps.branches.models import City
from apps.core.views import PermissionRequiredMixin


class BranchListView(PermissionRequiredMixin, ListView):
    required_action = "branch.list"
    queryset = selectors.branches()
    template_name = "branches/branch_list.html"
    context_object_name = "branches"
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
        self.filter_form = BranchFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            city = self.filter_form.cleaned_data["city"]
            status = self.filter_form.cleaned_data["status"]
            if city is not None:
                queryset = queryset.filter(city=city)
            if status:
                queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "filter_form": self.filter_form,
            "can_create": can(self.request.user, "branch.create"),
            "can_manage_cities": can(self.request.user, "city.manage"),
        }


def _detail_context(request, branch, errors=None):
    """Keep GET and failed POST renderings identical except for errors."""
    actions = (
        [
            action
            for state, action in services.BRANCH_TRANSITIONS
            if state == branch.status
        ]
        if can(request.user, "branch.transition", branch)
        else []
    )
    show_history = can(request.user, "audit.entity_history", branch)
    return {
        "branch": branch,
        "actions": actions,
        "can_edit": can(request.user, "branch.update", branch),
        "show_history": show_history,
        "history": selectors.branch_history(branch) if show_history else [],
        "errors": errors or [],
    }


class BranchDetailView(PermissionRequiredMixin, DetailView):
    required_action = "branch.view"
    queryset = selectors.branches()
    template_name = "branches/branch_detail.html"
    context_object_name = "branch"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            **_detail_context(self.request, self.object),
        }


class BranchCreateView(PermissionRequiredMixin, FormView):
    required_action = "branch.create"
    form_class = BranchCreateForm
    template_name = "branches/branch_form.html"
    extra_context = {"page_title": _("Create branch")}

    def form_valid(self, form):
        try:
            branch = services.create_branch(self.request.user, **form.cleaned_data)
        except ValidationError as error:
            _add_service_errors(form, error)
            return self.form_invalid(form)
        return redirect("branch-detail", pk=branch.pk)


class BranchEditView(BranchCreateView):
    required_action = "branch.update"
    form_class = BranchEditForm
    extra_context = {"page_title": _("Edit branch")}

    def get_branch(self):
        return get_object_or_404(
            scope_queryset(self.request.user, "branch.update", selectors.branches()),
            pk=self.kwargs["pk"],
        )

    def get_initial(self):
        branch = self.get_branch()
        return {field: getattr(branch, field) for field in services.EDITABLE_FIELDS}

    def form_valid(self, form):
        try:
            branch = services.update_branch(
                self.request.user, self.get_branch(), **form.cleaned_data
            )
        except ValidationError as error:
            _add_service_errors(form, error)
            return self.form_invalid(form)
        return redirect("branch-detail", pk=branch.pk)


class CityListView(PermissionRequiredMixin, ListView):
    required_action = "city.manage"
    queryset = City.objects.order_by("code")
    template_name = "branches/city_list.html"
    context_object_name = "cities"


class CityCreateView(PermissionRequiredMixin, FormView):
    required_action = "city.manage"
    form_class = CityCreateForm
    template_name = "branches/city_form.html"
    extra_context = {"page_title": _("Create city")}

    def form_valid(self, form):
        try:
            services.create_city(self.request.user, **form.cleaned_data)
        except ValidationError as error:
            _add_service_errors(form, error)
            return self.form_invalid(form)
        return redirect("city-list")


class CityEditView(CityCreateView):
    form_class = CityEditForm
    extra_context = {"page_title": _("Edit city")}

    def get_city(self):
        return get_object_or_404(
            scope_queryset(self.request.user, "city.manage", City.objects.all()),
            pk=self.kwargs["pk"],
        )

    def get_initial(self):
        city = self.get_city()
        return {"name_en": city.name_en, "name_ur": city.name_ur}

    def form_valid(self, form):
        try:
            services.update_city(
                self.request.user, self.get_city(), **form.cleaned_data
            )
        except ValidationError as error:
            _add_service_errors(form, error)
            return self.form_invalid(form)
        return redirect("city-list")


@require_POST
def branch_transition(request, pk, action):
    """Redirect successful actions; show conflicts beside the branch forms."""
    require(request.user, "branch.transition")
    scoped = scope_queryset(request.user, "branch.transition", selectors.branches())
    branch = get_object_or_404(scoped, pk=pk)
    try:
        services.transition(
            request.user, branch, action, request.POST.get("reason", "")
        )
    except (services.InvalidTransition, ValidationError) as error:
        branch = get_object_or_404(scoped, pk=pk)
        errors = error.messages if isinstance(error, ValidationError) else [str(error)]
        return render(
            request,
            "branches/branch_detail.html",
            {
                **_detail_context(request, branch, errors),
                "submitted_action": action,
                "submitted_reason": request.POST.get("reason", ""),
            },
            status=400 if isinstance(error, ValidationError) else 409,
        )
    messages.success(request, _("Branch status updated."))
    return redirect("branch-detail", pk=pk)


def _add_service_errors(form, error):
    """Put model validation errors beside a field when the form exposes it."""
    if hasattr(error, "message_dict"):
        for field, messages_for_field in error.message_dict.items():
            form.add_error(field if field in form.fields else None, messages_for_field)
    else:
        form.add_error(None, error)
