from uuid import UUID

import pytest
from django.http import HttpResponse

from apps.core.middleware import RequestIdMiddleware, request_id


@pytest.mark.parametrize("supplied_id", [None, "90d250cb-213b-45de-9368-c088de2fb150"])
def test_request_id_available_and_echoed(rf, supplied_id):
    headers = {"X-Request-ID": supplied_id} if supplied_id else {}
    request = rf.get("/en/", headers=headers)
    observed = []

    def get_response(request):
        observed.append(request_id.get())
        return HttpResponse()

    response = RequestIdMiddleware(get_response)(request)

    assert response["X-Request-ID"] == observed[0]
    if supplied_id:
        assert observed[0] == supplied_id
    else:
        assert str(UUID(observed[0])) == observed[0]
    assert request_id.get() is None


@pytest.mark.parametrize("supplied_id", ["", "judge-request-123", "abc\r\nInjected: 1"])
def test_invalid_request_id_replaced(rf, supplied_id):
    observed = []

    def get_response(request):
        observed.append(request_id.get())
        return HttpResponse()

    request = rf.get("/en/", headers={"X-Request-ID": supplied_id})
    response = RequestIdMiddleware(get_response)(request)
    generated_id = UUID(response["X-Request-ID"])

    assert generated_id.version == 4
    assert response["X-Request-ID"] == str(generated_id) == observed[0]
    assert response["X-Request-ID"] != supplied_id
    assert "Injected" not in response.headers
    assert request_id.get() is None


def test_request_id_reset_after_exception(rf):
    def get_response(request):
        raise RuntimeError("View failed")

    with pytest.raises(RuntimeError, match="View failed"):
        RequestIdMiddleware(get_response)(rf.get("/en/"))

    assert request_id.get() is None
