from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.accounts.permissions import require
from apps.seed.services import seed_demo


@require_POST
@login_required
def reset_demo(request):
    """Discard demo sessions with the reset, then flash on a fresh login session."""
    require(request.user, "demo.reset")
    if not settings.DEMO_MODE:
        raise Http404
    seed_demo(reset=True, triggered_by=request.user.email)
    request.session.flush()
    messages.success(request, _("Demo data reset. Please log in again."))
    return redirect("account-login")
