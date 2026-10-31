"""Small JSON stdout records without request bodies, tracebacks or credentials."""

import json
import logging
import re

from apps.core.context import request_id

EMAIL = re.compile(r"[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+")
PHONE = re.compile(r"(?<!\w)\+?\d[\d ()-]{8,}\d(?!\w)")
CREDENTIAL = re.compile(
    r"""(?:password|token|secret|authorization)["']?\s*[:=].*""",
    re.IGNORECASE,
)


class SafeJsonFormatter(logging.Formatter):
    """Keep operational context while excluding sensitive exception/request data."""

    def format(self, record):
        message = record.getMessage()
        if record.name.startswith(
            ("django.request", "django.security", "django.server")
        ):
            message = (
                "HTTP request completed"
                if record.levelno < logging.WARNING
                else "HTTP request failed"
            )
        message = EMAIL.sub("[email]", message)
        message = PHONE.sub("[phone]", message)
        message = CREDENTIAL.sub("[credential]", message)
        event = {
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id.get(),
            "message": message,
        }
        if record.exc_info:
            event["exception_type"] = record.exc_info[0].__name__
        return json.dumps(event, ensure_ascii=False)
