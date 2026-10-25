from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST
from django.views.generic import FormView, TemplateView

from apps.accounts import selectors, services
from apps.accounts.forms import ChangePasswordForm, LoginForm
from apps.core import rules


@method_decorator(sensitive_post_parameters("password"), name="dispatch")
class LoginView(FormView):
    template_name = "accounts/login.html"
    form_class = LoginForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(selectors.role_home_name(request.user))
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
class ChangePasswordView(LoginRequiredMixin, FormView):
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


class RoleHomeView(TemplateView):
    template_name = "accounts/role_home.html"
    allowed_roles = ()
    title = _("Staff area")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse("account-login"))
        if request.user.role not in self.allowed_roles:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "page_title": self.title}
