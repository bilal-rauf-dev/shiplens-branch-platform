from io import StringIO

import pytest
from django.conf import settings
from django.core.management import call_command
from django.http import HttpResponse
from django.test import RequestFactory
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import View

from apps.core.route_docs import view_methods


def test_t_doc_routes(tmp_path):
    output = tmp_path / "api.md"
    call_command("export_routes", output=output, stdout=StringIO())
    committed = settings.BASE_DIR / "docs" / "api.md"
    assert output.read_text(encoding="utf-8") == committed.read_text(encoding="utf-8")


class ReadView(View):
    def get(self, request):
        return HttpResponse()


@require_GET
def get_response(request):
    return HttpResponse()


@require_POST
def post_response(request):
    return HttpResponse()


@pytest.mark.parametrize(
    "callback",
    [ReadView.as_view(), get_response, post_response],
)
def test_documented_methods_match_django_dispatch(callback):
    methods = view_methods(callback).split(", ")
    factory = RequestFactory()
    for method in ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
        response = callback(factory.generic(method, "/"))
        assert (response.status_code != 405) == (method in methods)
