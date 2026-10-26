from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.accounts.permissions import require, scope_queryset
from apps.branches import services
from apps.branches.models import Branch


@require_POST
def branch_transition(request, pk, action):
    """Expose lifecycle conflicts as 409 without changing branch records."""
    require(request.user, "branch.transition")
    branch = get_object_or_404(
        scope_queryset(request.user, "branch.transition", Branch.objects.all()), pk=pk
    )
    try:
        services.transition(
            request.user, branch, action, request.POST.get("reason", "")
        )
    except services.InvalidTransition as error:
        return HttpResponse(
            str(error), status=409, content_type="text/plain; charset=utf-8"
        )
    except ValidationError as error:
        return HttpResponse(
            " ".join(error.messages),
            status=400,
            content_type="text/plain; charset=utf-8",
        )
    return HttpResponse(
        _("Branch status updated."), content_type="text/plain; charset=utf-8"
    )
