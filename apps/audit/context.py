from contextvars import ContextVar

# Only the explicitly captured fields are persisted, never request bodies/cookies.
request_context = ContextVar("audit_request_context", default=None)
