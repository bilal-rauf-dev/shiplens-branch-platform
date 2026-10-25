from apps.audit.context import request_context
from apps.core.middleware import request_id
from apps.core.net import client_ip


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = request_context.set(
            {
                "ip": client_ip(request),
                "user_agent": request.headers.get("User-Agent", "")[:200],
                "request_id": request_id.get(),
                "authenticated": request.user.is_authenticated,
            }
        )
        try:
            return self.get_response(request)
        finally:
            request_context.reset(token)
