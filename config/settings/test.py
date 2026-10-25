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
