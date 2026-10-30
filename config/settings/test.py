"""Tests use the configured PostgreSQL database and isolated Django test database."""

from .base import *  # noqa: F403

DEBUG = False
DATABASES["default"]["CONN_MAX_AGE"] = 0  # noqa: F405

# Unit tests render source assets; the Docker checks verify the production manifest.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
WHITENOISE_AUTOREFRESH = True

# Fast hashes keep ordinary tests quick; dedicated security tests use real Argon2.
# Base and production settings keep Argon2 as their first password hasher.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
