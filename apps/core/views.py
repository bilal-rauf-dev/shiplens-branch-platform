import os
from datetime import UTC

from django.http import JsonResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView

from apps.core import clock, selectors


class HomeView(TemplateView):
    template_name = "core/home.html"


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
