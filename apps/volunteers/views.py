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
from django.views.generic import DetailView, FormView, ListView

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
    MemberActionForm,
    MemberEditForm,
    MemberFilterForm,
    MemberLeftForm,
    MemberReinstateForm,
    ReassignApplicationForm,
    TeamForm,
    VolunteerRoleForm,
    age_on,
)
from apps.volunteers.models import ApplicationStatus, MemberStatus


def _management_errors(form, error):
    """Keep model-level errors visible without assuming they name a form field."""
    if hasattr(error, "message_dict"):
        for field, errors in error.message_dict.items():
            form.add_error(field if field in form.fields else None, errors)
    else:
        form.add_error(None, error)


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class MemberListView(PermissionRequiredMixin, ListView):
    required_action = "member.list"
    template_name = "volunteers/member_list.html"
    context_object_name = "members"
    paginate_by = 25

    def get_queryset(self):
        params = self.request.GET.copy()
        params.setdefault("status", MemberStatus.ACTIVE)
        self.filter_form = MemberFilterForm(params, user=self.request.user)
        if not self.filter_form.is_valid():
            return selectors.members().none()
        return selectors.search_members(
            self.request.user, self.filter_form.cleaned_data
        )

    def get_context_data(self, **kwargs):
        params = self.request.GET.copy()
        params.pop("page", None)
        return {
            **super().get_context_data(**kwargs),
            "filter_form": self.filter_form,
            "filter_query": params.urlencode(),
        }


class TeamListView(PermissionRequiredMixin, ListView):
    required_action = "team.list"
    queryset = selectors.teams()
    template_name = "volunteers/team_list.html"
    context_object_name = "teams"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "can_manage": can(self.request.user, "team.manage"),
            "managed_branches": selectors.team_management_branches(self.request.user),
        }


class TeamCreateView(PermissionRequiredMixin, FormView):
    required_action = "team.manage"
    form_class = TeamForm
    template_name = "volunteers/management_form.html"
    extra_context = {"page_title": _("Create team"), "return_route": "team-list"}

    def dispatch(self, request, *args, **kwargs):
        require(request.user, self.required_action)
        self.branch = get_object_or_404(
            selectors.team_management_branches(request.user), pk=kwargs["branch_pk"]
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            services.create_team(self.request.user, self.branch.pk, **form.cleaned_data)
        except ValidationError as error:
            _management_errors(form, error)
            return self.form_invalid(form)
        messages.success(self.request, _("Team created."))
        return redirect("team-list")

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "branch": self.branch}


class TeamEditView(PermissionRequiredMixin, FormView):
    required_action = "team.manage"
    form_class = TeamForm
    template_name = "volunteers/management_form.html"
    extra_context = {"page_title": _("Rename team"), "return_route": "team-list"}

    def dispatch(self, request, *args, **kwargs):
        require(request.user, self.required_action)
        self.team = get_object_or_404(
            scope_queryset(request.user, self.required_action, selectors.teams()),
            pk=kwargs["pk"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {"name": self.team.name}

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "branch": self.team.branch}

    def form_valid(self, form):
        try:
            services.rename_team(self.request.user, self.team.pk, **form.cleaned_data)
        except ValidationError as error:
            _management_errors(form, error)
            return self.form_invalid(form)
        messages.success(self.request, _("Team renamed."))
        return redirect("team-list")


@require_POST
def deactivate_team(request, pk):
    services.deactivate_team(request.user, pk)
    messages.success(request, _("Team deactivated."))
    return redirect("team-list")


class VolunteerRoleListView(PermissionRequiredMixin, ListView):
    required_action = "volunteer_role.manage"
    queryset = selectors.volunteer_roles()
    template_name = "volunteers/volunteer_role_list.html"
    context_object_name = "volunteer_roles"


class VolunteerRoleCreateView(PermissionRequiredMixin, FormView):
    required_action = "volunteer_role.manage"
    form_class = VolunteerRoleForm
    template_name = "volunteers/management_form.html"
    extra_context = {
        "page_title": _("Create volunteer role"),
        "return_route": "volunteer-role-list",
    }

    def form_valid(self, form):
        try:
            services.create_volunteer_role(self.request.user, **form.cleaned_data)
        except ValidationError as error:
            _management_errors(form, error)
            return self.form_invalid(form)
        messages.success(self.request, _("Volunteer role created."))
        return redirect("volunteer-role-list")


class VolunteerRoleEditView(VolunteerRoleCreateView):
    extra_context = {
        "page_title": _("Edit volunteer role"),
        "return_route": "volunteer-role-list",
    }

    def dispatch(self, request, *args, **kwargs):
        require(request.user, self.required_action)
        self.volunteer_role = get_object_or_404(
            scope_queryset(
                request.user, self.required_action, selectors.volunteer_roles()
            ),
            pk=kwargs["pk"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {
            "name_en": self.volunteer_role.name_en,
            "name_ur": self.volunteer_role.name_ur,
            "sort_order": self.volunteer_role.sort_order,
        }

    def form_valid(self, form):
        try:
            services.update_volunteer_role(
                self.request.user, self.volunteer_role.pk, **form.cleaned_data
            )
        except ValidationError as error:
            _management_errors(form, error)
            return self.form_invalid(form)
        messages.success(self.request, _("Volunteer role updated."))
        return redirect("volunteer-role-list")


@require_POST
def deactivate_volunteer_role(request, pk):
    services.deactivate_volunteer_role(request.user, pk)
    messages.success(request, _("Volunteer role deactivated."))
    return redirect("volunteer-role-list")


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
    """Show the existing member record, permitted actions and its audit history."""

    required_action = "member.view"
    queryset = selectors.members()
    template_name = "volunteers/member_detail.html"
    context_object_name = "member"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            **_member_context(self.request, self.object),
        }


MEMBER_ACTION_FORMS = {
    "deactivate": MemberActionForm,
    "reactivate": MemberActionForm,
    "mark_left": MemberLeftForm,
    "reinstate": MemberReinstateForm,
}
MEMBER_ACTION_LABELS = {
    "deactivate": _("Deactivate member"),
    "reactivate": _("Reactivate member"),
    "mark_left": _("Mark member left"),
    "reinstate": _("Reinstate member"),
}


def _member_context(request, member):
    actions = []
    for action, form_class in MEMBER_ACTION_FORMS.items():
        permission = "member.reinstate" if action == "reinstate" else "member.update"
        if (member.status, action) in services.MEMBER_TRANSITIONS and can(
            request.user, permission, member
        ):
            form = form_class(initial={"left_on": clock.today()})
            if action == "mark_left":
                form.fields["left_on"].widget.attrs["min"] = (
                    member.joined_on.isoformat()
                )
            actions.append(
                {
                    "route": "member-" + action.replace("_", "-"),
                    "label": MEMBER_ACTION_LABELS[action],
                    "form": form,
                }
            )
    show_history = can(request.user, "audit.entity_history", member)
    return {
        "member": member,
        "can_edit": can(request.user, "member.update", member),
        "actions": actions,
        "show_history": show_history,
        "history": selectors.member_history(request.user, member)
        if show_history
        else [],
    }


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class MemberEditView(PermissionRequiredMixin, FormView):
    required_action = "member.update"
    template_name = "volunteers/management_form.html"
    form_class = MemberEditForm
    extra_context = {"page_title": _("Edit member"), "return_route": "member-list"}

    def dispatch(self, request, *args, **kwargs):
        require(request.user, self.required_action)
        self.member = get_object_or_404(
            scope_queryset(request.user, self.required_action, selectors.members()),
            pk=kwargs["pk"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "member": self.member}

    def get_initial(self):
        return {
            "team_id": self.member.team_id,
            "role_id": self.member.volunteer_role_id,
            "phone": self.member.phone,
            "notes": self.member.notes,
        }

    def form_valid(self, form):
        try:
            services.update_member(
                self.request.user,
                self.member.pk,
                team_id=form.cleaned_data["team_id"].pk
                if form.cleaned_data["team_id"]
                else None,
                role_id=form.cleaned_data["role_id"].pk,
                phone=form.cleaned_data["phone"],
                notes=form.cleaned_data["notes"],
            )
        except ValidationError as error:
            _management_errors(form, error)
            return self.form_invalid(form)
        messages.success(self.request, _("Member updated."))
        return redirect("member-detail", pk=self.member.pk)


def _member_transition(request, pk, action):
    permission = "member.reinstate" if action == "reinstate" else "member.update"
    require(request.user, permission)
    member = get_object_or_404(
        scope_queryset(request.user, permission, selectors.members()), pk=pk
    )
    form = MEMBER_ACTION_FORMS[action](request.POST)
    error_status = 400
    if form.is_valid():
        try:
            services.transition_member(request.user, pk, action, **form.cleaned_data)
        except ValidationError as error:
            _management_errors(form, error)
        except InvalidTransition as error:
            form.add_error(None, str(error))
            error_status = 409
        else:
            messages.success(request, _("Member status updated."))
            return redirect("member-detail", pk=pk)
    context = _member_context(request, member)
    context["action_errors"] = form.errors
    return render(
        request, "volunteers/member_detail.html", context, status=error_status
    )


@cache_control(no_store=True, private=True)
@require_POST
def member_deactivate(request, pk):
    return _member_transition(request, pk, "deactivate")


@cache_control(no_store=True, private=True)
@require_POST
def member_reactivate(request, pk):
    return _member_transition(request, pk, "reactivate")


@cache_control(no_store=True, private=True)
@require_POST
def member_mark_left(request, pk):
    return _member_transition(request, pk, "mark_left")


@cache_control(no_store=True, private=True)
@require_POST
def member_reinstate(request, pk):
    return _member_transition(request, pk, "reinstate")
