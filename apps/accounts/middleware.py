"""Enforce session time limits and temporary-password changes before staff pages."""

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.urls import reverse

from apps.accounts import services
from apps.core import clock, rules


class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            current = clock.now().timestamp()
            started = request.session.get("auth_started_at")
            last_activity = request.session.get("auth_last_activity_at")
            if started is None or last_activity is None:
                services.start_session_deadline(request)
            elif current - started >= rules.get(
                "session_absolute_seconds"
            ) or current - last_activity >= rules.get("session_idle_seconds"):
                services.sign_out(request)
                return redirect_to_login(
                    request.get_full_path(), reverse("account-login")
                )
            else:
                request.session["auth_last_activity_at"] = current
        return self.get_response(request)


class MustChangePasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # The route registry checks registration before this redirect is considered.
        if request.user.is_authenticated and request.user.must_change_password:
            exempt_paths = {
                reverse("account-change-password"),
                reverse("account-logout"),
                "/health",
            }
            if request.path not in exempt_paths and not request.path.startswith(
                settings.STATIC_URL
            ):
                return redirect("account-change-password")
        return None
