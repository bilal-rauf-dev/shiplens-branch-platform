from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, FormView, ListView, TemplateView
from django.views.i18n import set_language as django_set_language

from apps.accounts import selectors, services
from apps.accounts.forms import (
    BranchAssignmentForm,
    ChangePasswordForm,
    LoginForm,
    SystemSettingsForm,
    UserCreateForm,
    UserEditForm,
)
from apps.accounts.permissions import require, scope_queryset
from apps.core import rules
from apps.core.views import PermissionRequiredMixin


@method_decorator(sensitive_post_parameters("password"), name="dispatch")
class LoginView(FormView):
    template_name = "accounts/login.html"
    form_class = LoginForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(selectors.role_home_name(request.user))
        if request.method == "POST" and services.login_rate_limited(request):
            return render(
                request,
                "429.html",
                {
                    "rate_limit_message": _(
                        "Too many login attempts from this connection. "
                        "Please try again later."
                    )
                },
                status=429,
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "request": self.request}

    def form_valid(self, form):
        services.sign_in(self.request, form.user)
        destination = (
            "account-change-password"
            if form.user.must_change_password
            else selectors.role_home_name(form.user)
        )
        return redirect(destination)


@method_decorator(
    sensitive_post_parameters("old_password", "new_password1", "new_password2"),
    name="dispatch",
)
class ChangePasswordView(PermissionRequiredMixin, FormView):
    required_action = "account.change_password"
    template_name = "accounts/change_password.html"
    form_class = ChangePasswordForm

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def form_valid(self, form):
        try:
            user = services.change_password(
                self.request,
                form.cleaned_data["old_password"],
                form.cleaned_data["new_password1"],
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        return HttpResponseRedirect(reverse(selectors.role_home_name(user)))


@require_POST
@login_required
def logout(request):
    services.sign_out(request)
    return redirect("account-login")


def locked_out(request, response=None, credentials=None):
    """Show a localised lockout message without echoing credentials."""
    return render(
        request,
        "accounts/login.html",
        {
            "form": LoginForm(request=request),
            "locked_out": True,
            "cooloff_minutes": rules.get("auth_cooloff_minutes"),
        },
        status=429,
    )


class RoleHomeView(PermissionRequiredMixin, TemplateView):
    template_name = "accounts/role_home.html"
    title = _("Staff area")

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "page_title": self.title}


@sensitive_variables()
def _temporary_password_response(request, user, temporary):
    """Display a generated secret only in this response, never in URLs or sessions."""
    response = render(
        request,
        "accounts/temporary_password.html",
        {
            "account": user,
            "temporary_password": temporary,
        },
    )
    response["Cache-Control"] = "no-store, private"
    response["Pragma"] = "no-cache"
    response["Referrer-Policy"] = "no-referrer"
    return response


class UserListView(PermissionRequiredMixin, ListView):
    required_action = "user.list"
    queryset = selectors.users()
    template_name = "accounts/user_list.html"
    context_object_name = "accounts"


class UserDetailView(PermissionRequiredMixin, DetailView):
    required_action = "user.view"
    queryset = selectors.users().prefetch_related("branch_assignments__branch")
    template_name = "accounts/user_detail.html"
    context_object_name = "account"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "assignment_form": BranchAssignmentForm(),
        }


class UserCreateView(PermissionRequiredMixin, FormView):
    required_action = "user.create"
    form_class = UserCreateForm
    template_name = "accounts/user_form.html"
    extra_context = {"page_title": _("Create user")}

    @sensitive_variables()
    def form_valid(self, form):
        try:
            user, temporary = services.create_user(
                self.request.user, **form.cleaned_data
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        return _temporary_password_response(self.request, user, temporary)


class UserEditView(PermissionRequiredMixin, FormView):
    required_action = "user.update"
    form_class = UserEditForm
    template_name = "accounts/user_form.html"
    extra_context = {"page_title": _("Edit user")}

    def get_account(self):
        return get_object_or_404(
            scope_queryset(self.request.user, self.required_action, selectors.users()),
            pk=self.kwargs["pk"],
        )

    def get_initial(self):
        account = self.get_account()
        return {"full_name": account.full_name, "role": account.role}

    def form_valid(self, form):
        try:
            user = services.update_user(
                self.request.user, self.get_account(), **form.cleaned_data
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        return redirect("user-detail", pk=user.pk)


@require_POST
def deactivate_user(request, pk):
    require(request.user, "user.update")
    account = get_object_or_404(
        scope_queryset(request.user, "user.update", selectors.users()), pk=pk
    )
    try:
        account = services.set_user_active(request.user, account, active=False)
    except ValidationError as error:
        return render(
            request,
            "accounts/action_error.html",
            {"errors": error.messages},
            status=409,
        )
    if request.user.pk == account.pk:
        services.sign_out(request)
        return redirect("account-login")
    return redirect("user-detail", pk=account.pk)


@require_POST
def reactivate_user(request, pk):
    require(request.user, "user.update")
    account = get_object_or_404(
        scope_queryset(request.user, "user.update", selectors.users()), pk=pk
    )
    services.set_user_active(request.user, account, active=True)
    return redirect("user-detail", pk=pk)


@require_POST
@sensitive_variables()
def reset_user_password(request, pk):
    require(request.user, "user.reset_password")
    account = get_object_or_404(
        scope_queryset(request.user, "user.reset_password", selectors.users()), pk=pk
    )
    account, temporary = services.reset_temporary_password(request.user, account)
    if request.user.pk == account.pk:
        services.sign_out(request)
    return _temporary_password_response(request, account, temporary)


@require_POST
def assign_user_branch(request, pk):
    require(request.user, "assignment.manage")
    account = get_object_or_404(
        scope_queryset(request.user, "assignment.manage", selectors.users()), pk=pk
    )
    form = BranchAssignmentForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "accounts/action_error.html",
            {"errors": form.errors.values()},
            status=400,
        )
    branch = get_object_or_404(
        scope_queryset(request.user, "branch.view", selectors.assignable_branches()),
        pk=form.cleaned_data["branch_id"],
    )
    try:
        services.assign_branch(request.user, account, branch)
    except ValidationError as error:
        return render(
            request,
            "accounts/action_error.html",
            {"errors": error.messages},
            status=409,
        )
    return redirect("user-detail", pk=pk)


@require_POST
def remove_user_branch(request, pk, branch_id):
    require(request.user, "assignment.manage")
    account = get_object_or_404(
        scope_queryset(request.user, "assignment.manage", selectors.users()), pk=pk
    )
    services.remove_branch_assignment(request.user, account, branch_id)
    return redirect("user-detail", pk=pk)


class SettingsView(PermissionRequiredMixin, FormView):
    required_action = "settings.view"
    form_class = SystemSettingsForm
    template_name = "accounts/settings.html"
    http_method_names = ["get"]

    def get_initial(self):
        return {key: rules.get(key) for key in services.EDITABLE_SETTINGS}


class SettingsUpdateView(SettingsView):
    required_action = "settings.update"
    http_method_names = ["post"]

    def form_valid(self, form):
        try:
            services.update_settings(self.request.user, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        return redirect("settings-view")


@require_POST
def set_language(request):
    """Use Django's safe redirect and cookie, persisting signed-in preferences."""
    language = request.POST.get("language")
    if request.user.is_authenticated and language in dict(settings.LANGUAGES):
        services.set_preferred_language(request.user, language)
    return django_set_language(request)
