"""Production settings with HTTPS and host-only secure cookies."""

from copy import deepcopy

from .base import *  # noqa: F403

DEBUG = False
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# Preloading is deliberately disabled: we do not own the shared onrender.com domain.
SILENCED_SYSTEM_CHECKS = ["security.W021"]
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_NAME = "__Host-sid"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_NAME = "__Host-csrftoken"
LANGUAGE_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

SESSION_COOKIE_PATH = "/"
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_PATH = "/"
CSRF_COOKIE_DOMAIN = None

# Cloud connections require TLS by default. Only isolated local smoke stacks opt out.
# Copy before editing: importing prod must not mutate base/dev/test configuration.
DATABASES = deepcopy(DATABASES)  # noqa: F405
DATABASES["default"].setdefault("OPTIONS", {}).setdefault("sslmode", "require")
