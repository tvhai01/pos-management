"""
Django base settings for POS Management System.

Shared across all environments. Environment-specific settings override
values defined here via `development.py` or `production.py`.

For the full list of settings and their values, see
https://docs.djangoproject.com/en/6.0/ref/settings/
"""

import logging
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

# =============================================================================
# Path Configuration
# =============================================================================

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR points to the project root (where manage.py lives).
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

# =============================================================================
# Core Settings
# =============================================================================

SECRET_KEY: str = config("DJANGO_SECRET_KEY", cast=str)

DEBUG: bool = config("DJANGO_DEBUG", default=False, cast=bool)

ALLOWED_HOSTS: list[str] = config(
    "DJANGO_ALLOWED_HOSTS",
    default="localhost,127.0.0.1",
    cast=Csv(),
)

# =============================================================================
# Application Definition
# =============================================================================

DJANGO_APPS: list[str] = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS: list[str] = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
]

LOCAL_APPS: list[str] = [
    "apps.accounts",
    "apps.customers",
    "apps.dashboard",
    "apps.invoices",
    "apps.orders",
    "apps.payments",
    "apps.product",
    "apps.inventory",
    "apps.reports",
]

INSTALLED_APPS: list[str] = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# =============================================================================
# Middleware
# =============================================================================

MIDDLEWARE: list[str] = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# =============================================================================
# URL Configuration
# =============================================================================

ROOT_URLCONF: str = "config.urls"

# =============================================================================
# Templates
# =============================================================================

TEMPLATES: list[dict] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# =============================================================================
# WSGI / ASGI
# =============================================================================

WSGI_APPLICATION: str = "config.wsgi.application"
ASGI_APPLICATION: str = "config.asgi.application"

# =============================================================================
# Database — PostgreSQL Only
# =============================================================================
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES: dict = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB", default="pos_db"),
        "USER": config("POSTGRES_USER", default="pos_user"),
        "PASSWORD": config("POSTGRES_PASSWORD", default="pos_password"),
        "HOST": config("POSTGRES_HOST", default="localhost"),
        "PORT": config("POSTGRES_PORT", default="5432"),
        "OPTIONS": {
            "connect_timeout": 5,
        },
    }
}

# =============================================================================
# Cache — Redis
# =============================================================================

CACHES: dict = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://localhost:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# Use Redis for session storage.
SESSION_ENGINE: str = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS: str = "default"

# =============================================================================
# Custom User Model
# =============================================================================

AUTH_USER_MODEL: str = "accounts.User"

# =============================================================================
# Session Auth — Dashboard (server-rendered admin UI)
# =============================================================================
# Separate from JWT (used by the API). `apps.dashboard` authenticates via
# Django sessions so a browser-based login can set cookies normally.

LOGIN_URL: str = "dashboard:login"
LOGIN_REDIRECT_URL: str = "dashboard:index"
LOGOUT_REDIRECT_URL: str = "dashboard:login"

# =============================================================================
# Password Validation
# =============================================================================
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS: list[dict] = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# =============================================================================
# Internationalization
# =============================================================================

LANGUAGE_CODE: str = "en-us"

TIME_ZONE: str = "Asia/Ho_Chi_Minh"

USE_I18N: bool = True

USE_TZ: bool = True

# =============================================================================
# Static Files
# =============================================================================
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL: str = "/static/"
STATIC_ROOT: Path = BASE_DIR / "staticfiles"
STATICFILES_DIRS: list[Path] = [BASE_DIR / "static"]

# =============================================================================
# Media Files
# =============================================================================

MEDIA_URL: str = "/media/"
MEDIA_ROOT: Path = BASE_DIR / "media"

# =============================================================================
# Default Primary Key Field Type
# =============================================================================

DEFAULT_AUTO_FIELD: str = "django.db.models.BigAutoField"

# =============================================================================
# Django REST Framework
# =============================================================================

REST_FRAMEWORK: dict = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "shared.pagination.StandardPageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "EXCEPTION_HANDLER": "shared.exceptions.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
    "DATE_FORMAT": "%Y-%m-%d",
    "TIME_FORMAT": "%H:%M:%S",
}

# =============================================================================
# SimpleJWT
# =============================================================================

SIMPLE_JWT: dict = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=30, cast=int)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7, cast=int)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

# =============================================================================
# CORS
# =============================================================================

CORS_ALLOWED_ORIGINS: list[str] = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000",
    cast=Csv(),
)

CORS_ALLOW_CREDENTIALS: bool = True

# =============================================================================
# Payment provider
# =============================================================================

SEPAY_ENV: str = config("SEPAY_ENV", default="sandbox")
SEPAY_MERCHANT_ID: str = config("SEPAY_MERCHANT_ID", default="")
SEPAY_SECRET_KEY: str = config("SEPAY_SECRET_KEY", default="")
SEPAY_KEY: str = config("SEPAY_KEY", default="")
SEPAY_WEBHOOK_SECRET: str = config(
    "SEPAY_WEBHOOK_SECRET", default=SEPAY_SECRET_KEY
)
SEPAY_BANK_ACCOUNT_XID: str = config("SEPAY_BANK_ACCOUNT_XID", default="")
SEPAY_API_URL: str = config(
    "SEPAY_API_URL",
    default="https://userapi-sandbox.sepay.vn/v2",
)
VIETQR_BANK_ID: str = config("VIETQR_BANK_ID", default="VCB")
VIETQR_ACCOUNT_NUMBER: str = config("VIETQR_ACCOUNT_NUMBER", default="")
VIETQR_ACCOUNT_NAME: str = config("VIETQR_ACCOUNT_NAME", default="")

# =============================================================================
# Report AI Insight — see apps/reports/ai/
# =============================================================================
# Missing keys are expected in dev/CI: ReportInsightService falls back to a
# rule-based generator, so the feature always works without either provider.

GEMINI_API_KEY: str = config("GEMINI_API_KEY", default="")
GEMINI_API_URL: str = config(
    "GEMINI_API_URL",
    default="https://generativelanguage.googleapis.com/v1beta/models",
)
GEMINI_MODEL: str = config("GEMINI_MODEL", default="gemini-2.0-flash")

GROQ_API_KEY: str = config("GROQ_API_KEY", default="")
GROQ_API_URL: str = config(
    "GROQ_API_URL",
    default="https://api.groq.com/openai/v1/chat/completions",
)
GROQ_MODEL: str = config("GROQ_MODEL", default="llama-3.3-70b-versatile")

AI_INSIGHT_TIMEOUT: int = config("AI_INSIGHT_TIMEOUT", default=10, cast=int)
AI_INSIGHT_CACHE_TTL: int = config("AI_INSIGHT_CACHE_TTL", default=900, cast=int)

# =============================================================================
# Application Version
# =============================================================================

APP_VERSION: str = config("APP_VERSION", default="0.1.0")

# =============================================================================
# Logging
# =============================================================================

LOGGING: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": config("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "apps": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

logger = logging.getLogger(__name__)
