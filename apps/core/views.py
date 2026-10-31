import os
from datetime import UTC

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import get_language, get_language_bidi
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView

from apps.accounts.permissions import require, scope_queryset
from apps.core import clock, selectors


class PermissionRequiredMixin:
    """Apply the central action check and assigned-branch scope to generic views."""

    required_action = None
    branch_field = "branch_id"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse("account-login"))
        require(request.user, self.required_action)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Scope generic list/detail views before Django looks up an object."""
        return scope_queryset(
            self.request.user,
            self.required_action,
            super().get_queryset(),
            branch_field=self.branch_field,
        )


class HomeView(TemplateView):
    template_name = "core/home.html"


def _error_response(template_name, status):
    """Avoid request context processors: even a database failure needs an error page."""
    content = render_to_string(
        template_name,
        {"LANGUAGE_CODE": get_language(), "LANGUAGE_BIDI": get_language_bidi()},
    )
    return HttpResponse(content, status=status)


def permission_denied(request, exception):
    return _error_response("403.html", 403)


def page_not_found(request, exception):
    return _error_response("404.html", 404)


def server_error(request):
    return _error_response("500.html", 500)


@cache_control(no_store=True)
@require_GET
def health(request):
    """Expose readiness to hosting checks without disclosing database errors."""
    try:
        database_ok = selectors.check_database()
    except Exception:
        # A failed probe must produce the same small response for every DB error.
        database_ok = False

    if not database_ok:
        return JsonResponse({"status": "degraded", "db": "error"}, status=503)

    version = os.environ.get("RENDER_GIT_COMMIT") or os.environ.get("GIT_SHA") or "dev"
    return JsonResponse(
        {
            "status": "ok",
            "db": "ok",
            "version": version[:7],
            "time": clock.now().astimezone(UTC).isoformat().replace("+00:00", "Z"),
        }
    )


def csrf_failure(request, reason=""):
    """Return the same localized denial page without exposing CSRF diagnostics."""
    return _error_response("403.html", 403)
