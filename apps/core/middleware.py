"""Keep a correlation ID local to each request."""

from contextvars import ContextVar
from uuid import UUID, uuid4

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import reverse

from apps.accounts.permissions import can
from apps.audit.services import record_denial
from apps.core import views
from apps.core.routes import PUBLIC_ROUTES, ROUTE_ACTIONS

request_id = ContextVar("request_id", default=None)


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Probes use IP addresses over internal HTTP; this endpoint exposes no secrets.
        if request.path == "/health":
            return views.health(request)
        return self.get_response(request)


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            correlation_id = str(UUID(request.headers.get("X-Request-ID", "")))
        except ValueError:
            correlation_id = str(uuid4())
        token = request_id.set(correlation_id)
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = correlation_id
            return response
        finally:
            # Reset even when a request fails, so the next request cannot inherit it.
            request_id.reset(token)


class RouteRegistryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Authorize after URL resolution and before any view can run."""
        if request.path == "/health" or request.path.startswith(settings.STATIC_URL):
            return None
        # Include namespaces so an unrelated route cannot borrow a registered name.
        route_name = request.resolver_match.view_name
        if route_name in PUBLIC_ROUTES:
            return None
        if route_name not in ROUTE_ACTIONS:
            raise Http404
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse("account-login"))
        if not can(request.user, ROUTE_ACTIONS[route_name]):
            record_denial(request.user, route_name, ROUTE_ACTIONS[route_name])
            raise PermissionDenied
        return None


class SecurityHeadersMiddleware:
    """Apply browser isolation headers even to internal HTTP health responses.

    CSP and this middleware wrap the health shortcut; Django's SSL redirect and
    host validation remain inside it so internal probes can still call by IP.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        )
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Cross-Origin-Opener-Policy"] = "same-origin"
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("X-Frame-Options", "DENY")
        return response
