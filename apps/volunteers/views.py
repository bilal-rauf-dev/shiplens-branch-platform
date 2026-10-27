"""Public form responses expose a reference only, never duplicate or review data."""

import re
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_control
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.views.generic import DetailView, ListView

from apps.accounts.permissions import can, require, scope_queryset
from apps.core import clock
from apps.core.exceptions import InvalidTransition
from apps.core.net import client_ip
from apps.core.views import PermissionRequiredMixin
from apps.volunteers import selectors, services
from apps.volunteers.constants import AVAILABILITY, INTERESTS
from apps.volunteers.forms import (
    AcceptApplicationForm,
    ApplicationFilterForm,
    ApplicationForm,
    DeclineApplicationForm,
    ReassignApplicationForm,
    age_on,
)
from apps.volunteers.models import ApplicationStatus


def _thanks(reference):
    return redirect(reverse("volunteer-thanks") + "?" + urlencode({"ref": reference}))


@cache_control(no_store=True)
@sensitive_post_parameters("full_name", "email", "phone", "date_of_birth", "motivation")
@require_http_methods(["GET", "POST"])
def apply(request):
    if request.method == "POST":
        if services.application_rate_limited(request):
            return render(request, "429.html", status=429)
        reason = services.spam_reason(request.POST)
        if reason is not None:
            return _thanks(services.discard_spam(reason))
        form = ApplicationForm(request.POST)
        if form.is_valid():
            try:
                application = services.submit_application(
                    form.cleaned_data, client_ip(request)
                )
            except ValidationError as error:
                for field, errors in error.message_dict.items():
                    form.add_error(field, errors)
            else:
                return _thanks(application.reference)
    else:
        form = ApplicationForm()
    return render(request, "volunteers/application_form.html", {"form": form})


@require_GET
def thanks(request):
    reference = request.GET.get("ref", "")
    if re.fullmatch(r"APP-[0-9]{4}-[0-9]{5,7}", reference) is None:
        reference = ""
    return render(request, "volunteers/thanks.html", {"reference": reference})


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class ApplicationListView(PermissionRequiredMixin, ListView):
    required_action = "application.list"
    queryset = selectors.applications()
    template_name = "volunteers/application_list.html"
    context_object_name = "applications"
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
        self.filter_form = ApplicationFilterForm(
            self.request.GET, user=self.request.user
        )
        self.selected_status = ApplicationStatus.PENDING
        if not self.filter_form.is_valid():
            return queryset.none()
        self.selected_status = (
            self.filter_form.cleaned_data["status"] or ApplicationStatus.PENDING
        )
        queryset = queryset.filter(status=self.selected_status)
        branch = self.filter_form.cleaned_data["branch_id"]
        return (
            queryset.filter(preferred_branch=branch) if branch is not None else queryset
        )

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "filter_form": self.filter_form,
            "selected_status": self.selected_status,
            "status_choices": ApplicationStatus.choices,
        }


def _detail_context(request, application):
    """Only instantiate decision forms and duplicate links the user may access."""
    pending = application.status == ApplicationStatus.PENDING
    show_history = can(request.user, "audit.entity_history", application)
    context = {
        "application": application,
        "age": age_on(application.date_of_birth, clock.today()),
        "interests": [
            dict(INTERESTS).get(value, value) for value in application.interests
        ],
        "availability": [
            dict(AVAILABILITY).get(value, value) for value in application.availability
        ],
        "duplicates": selectors.duplicate_records(request.user, application)
        if application.possible_duplicate
        else {},
        "show_history": show_history,
        "history": selectors.application_history(request.user, application)
        if show_history
        else [],
        "accept_form": None,
        "decline_form": None,
        "reassign_form": None,
        "created_member": application.member
        if application.member_id
        and can(request.user, "member.view", application.member)
        else None,
    }
    if pending and can(request.user, "application.accept", application):
        context["accept_form"] = AcceptApplicationForm(application=application)
    if pending and can(request.user, "application.decline", application):
        context["decline_form"] = DeclineApplicationForm()
    if pending and can(request.user, "application.reassign_branch", application):
        context["reassign_form"] = ReassignApplicationForm(
            initial={"branch_id": application.preferred_branch_id}
        )
    return context


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class ApplicationDetailView(PermissionRequiredMixin, DetailView):
    required_action = "application.view"
    queryset = selectors.applications()
    template_name = "volunteers/application_detail.html"
    context_object_name = "application"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            **_detail_context(self.request, self.object),
        }


def _review_application(request, pk, action):
    require(request.user, action)
    return get_object_or_404(
        scope_queryset(request.user, action, selectors.applications()), pk=pk
    )


def _review_error(request, pk, form, form_name, *, status, error=None):
    application = _review_application(request, pk, "application.view")
    context = _detail_context(request, application)
    if context[form_name] is not None:
        context[form_name] = form
    context["errors"] = (
        [str(error)] if error is not None else [_("Please correct the errors below.")]
    )
    return render(request, "volunteers/application_detail.html", context, status=status)


def _service_errors(form, error):
    if hasattr(error, "message_dict"):
        for field, errors in error.message_dict.items():
            form.add_error(field if field in form.fields else None, errors)
    else:
        form.add_error(None, error)


@cache_control(no_store=True, private=True)
@require_POST
def accept(request, pk):
    application = _review_application(request, pk, "application.accept")
    form = AcceptApplicationForm(request.POST, application=application)
    if not form.is_valid():
        return _review_error(request, pk, form, "accept_form", status=400)
    try:
        team = form.cleaned_data["team_id"]
        member = services.accept_application(
            request.user,
            pk,
            team_id=team.pk if team else None,
            role_id=form.cleaned_data["role_id"].pk,
        )
    except InvalidTransition as error:
        return _review_error(request, pk, form, "accept_form", status=409, error=error)
    except ValidationError as error:
        _service_errors(form, error)
        return _review_error(request, pk, form, "accept_form", status=400)
    messages.success(
        request, _("Member %(member_id)s created.") % {"member_id": member.member_id}
    )
    return redirect("application-detail", pk=pk)


@cache_control(no_store=True, private=True)
@require_POST
def decline(request, pk):
    _review_application(request, pk, "application.decline")
    form = DeclineApplicationForm(request.POST)
    if not form.is_valid():
        return _review_error(request, pk, form, "decline_form", status=400)
    try:
        services.decline_application(request.user, pk, form.cleaned_data["reason"])
    except InvalidTransition as error:
        return _review_error(request, pk, form, "decline_form", status=409, error=error)
    except ValidationError as error:
        _service_errors(form, error)
        return _review_error(request, pk, form, "decline_form", status=400)
    messages.success(request, _("Application declined."))
    return redirect("application-detail", pk=pk)


@cache_control(no_store=True, private=True)
@require_POST
def reassign(request, pk):
    _review_application(request, pk, "application.reassign_branch")
    form = ReassignApplicationForm(request.POST)
    if not form.is_valid():
        return _review_error(request, pk, form, "reassign_form", status=400)
    try:
        application = services.reassign_branch(
            request.user, pk, form.cleaned_data["branch_id"].pk
        )
    except InvalidTransition as error:
        return _review_error(
            request, pk, form, "reassign_form", status=409, error=error
        )
    except ValidationError as error:
        _service_errors(form, error)
        return _review_error(request, pk, form, "reassign_form", status=400)
    messages.success(request, _("Application reassigned."))
    if can(request.user, "application.view", application):
        return redirect("application-detail", pk=pk)
    return redirect("application-list")


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class MemberDetailView(PermissionRequiredMixin, DetailView):
    """Provide a scoped, read-only destination for matched-member links."""

    required_action = "member.view"
    queryset = selectors.members()
    template_name = "volunteers/member_detail.html"
    context_object_name = "member"
