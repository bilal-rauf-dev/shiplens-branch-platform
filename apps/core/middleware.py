"""Keep a correlation ID local to each request."""

from contextvars import ContextVar
from uuid import UUID, uuid4

from apps.core import views

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
