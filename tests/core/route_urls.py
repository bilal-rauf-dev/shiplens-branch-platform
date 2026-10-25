"""Test-only routes exercise failures without exposing them in the application."""

from django.conf.urls.i18n import i18n_patterns
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.urls import include, path
from django.views.generic import DetailView

from apps.branches.models import Branch
from apps.core.views import PermissionRequiredMixin
from config import urls as application_urls

handler403 = application_urls.handler403
handler404 = application_urls.handler404
handler500 = application_urls.handler500


def unreachable(request):
    raise AssertionError("An unregistered view must never run")


def denied(request):
    raise PermissionDenied("private entity details")


def crash(request):
    raise RuntimeError("private database details")


class BranchDetail(PermissionRequiredMixin, DetailView):
    model = Branch
    required_action = "branch.view"

    def render_to_response(self, context, **response_kwargs):
        return HttpResponse(context["object"].code)


urlpatterns = [*application_urls.urlpatterns]
urlpatterns += i18n_patterns(
    path("registry/unregistered/", unreachable, name="unregistered"),
    path("registry/unnamed/", unreachable),
    path(
        "registry/namespaced/",
        include(
            ([path("", unreachable, name="home")], "fixture"), namespace="collision"
        ),
    ),
    path("registry/denied/", denied, name="registry-denied"),
    path("registry/crash/", crash, name="registry-crash"),
    path("registry/branches/<int:pk>/", BranchDetail.as_view(), name="registry-branch"),
)
