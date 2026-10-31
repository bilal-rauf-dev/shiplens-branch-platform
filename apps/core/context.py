"""Request correlation without importing Django models during logging setup."""

from contextvars import ContextVar

request_id = ContextVar("request_id", default=None)
