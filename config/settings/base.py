"""Shared configuration; secrets and deployment addresses come from the environment."""

import os
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "")
TRUSTED_PROXY_HOPS = int(os.environ.get("TRUSTED_PROXY_HOPS", "1"))
if TRUSTED_PROXY_HOPS < 0:
    raise ImproperlyConfigured("TRUSTED_PROXY_HOPS cannot be negative.")

DATABASES = {
    "default": dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=60)
}
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("DATABASE_URL must use PostgreSQL.")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "apps.core.apps.CoreConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.branches.apps.BranchesConfig",
    "apps.audit.apps.AuditConfig",
    "apps.volunteers.apps.VolunteersConfig",
    "apps.finance.apps.FinanceConfig",
    "axes",
]
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "apps.accounts.backends.EmailBackend",
]
LOGIN_URL = "account-login"
MIDDLEWARE = [
    "apps.core.middleware.HealthCheckMiddleware",
    "apps.core.middleware.RequestIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.audit.middleware.AuditContextMiddleware",
    "apps.accounts.middleware.SessionTimeoutMiddleware",
    "apps.core.middleware.RouteRegistryMiddleware",
    "apps.accounts.middleware.MustChangePasswordMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

TIME_ZONE = "Asia/Karachi"
USE_TZ = True
USE_I18N = True
LANGUAGE_CODE = "en"
LANGUAGES = [("en", _("English")), ("ur", _("اردو"))]
LOCALE_PATHS = [BASE_DIR / "locale"]
LANGUAGE_COOKIE_HTTPONLY = True
LANGUAGE_COOKIE_SAMESITE = "Lax"
LANGUAGE_COOKIE_AGE = 31536000

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "shiplens_cache",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher"]

# Defaults from docs/planning/07-business-rules.md; DB overrides arrive in P2.
BUSINESS_RULES = {
    "login_rate_per_minute": 20,
    "login_rate_per_day": 200,
    "application_decline_reason_min_length": 5,
    "application_decline_reason_max_length": 500,
    "application_name_min_length": 3,
    "application_name_max_length": 100,
    "application_motivation_min_length": 20,
    "application_motivation_max_length": 1000,
    "application_max_interests": 5,
    "volunteer_max_age": 100,
    "guardian_consent_age": 18,
    "form_max_seconds": 2 * 60 * 60,
    "apply_rate_per_day": 20,
    "branch_reason_min_length": 5,
    "branch_reason_max_length": 300,
    "temporary_password_bytes": 24,
    "collection_lock_days_min": 1,
    "collection_lock_days_max": 30,
    "min_volunteer_age_min": 14,
    "min_volunteer_age_max": 25,
    "apply_rate_per_hour_min": 1,
    "apply_rate_per_hour_max": 50,
    "audit_denial_seconds": 60,
    "password_min_length": 12,
    "auth_failure_limit": 5,
    "auth_cooloff_minutes": 15,
    "session_absolute_seconds": 8 * 60 * 60,
    "session_idle_seconds": 60 * 60,
    "min_volunteer_age": 16,  # BR-043
    "form_min_seconds": 3,  # BR-051
    "apply_rate_per_hour": 5,  # BR-051
    "max_collection": Decimal("10000000.00"),  # BR-060
    "collection_lock_days": 7,  # BR-064
    "collection_void_reason_min_length": 5,
    "collection_void_reason_max_length": 300,
    "week_start_day": "MON",  # BR-080
    "allow_submit_current_week": False,  # BR-085
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": BUSINESS_RULES["password_min_length"]},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
        "OPTIONS": {"user_attributes": ["email", "full_name"]},
    },
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
AXES_FAILURE_LIMIT = BUSINESS_RULES["auth_failure_limit"]
AXES_COOLOFF_TIME = timedelta(minutes=BUSINESS_RULES["auth_cooloff_minutes"])
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_CLIENT_IP_CALLABLE = "apps.core.net.client_ip"
AXES_USERNAME_FORM_FIELD = "email"
AXES_USERNAME_CALLABLE = "apps.accounts.backends.login_email"
AXES_LOCKOUT_CALLABLE = "apps.accounts.views.locked_out"
AXES_RESET_ON_SUCCESS = True
AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT = False
AXES_ENABLE_ADMIN = False
AXES_SENSITIVE_PARAMETERS = ["username", "email", "ip_address", "user_agent"]
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = BUSINESS_RULES["session_absolute_seconds"]
SESSION_SAVE_EVERY_REQUEST = False

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler", "stream": "ext://sys.stdout"}
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}
