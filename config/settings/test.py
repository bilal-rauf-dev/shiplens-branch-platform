"""Tests use the configured PostgreSQL database and isolated Django test database."""

from .base import *  # noqa: F403

DEBUG = False
DATABASES["default"]["CONN_MAX_AGE"] = 0  # noqa: F405
