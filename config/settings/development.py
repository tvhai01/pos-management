"""
Django development settings for POS Management System.

Extends base settings with development-specific overrides.
- DEBUG enabled
- Django Debug Toolbar
- Browsable API renderer
- Console email backend
"""

from config.settings.base import *  # noqa: F401, F403
from config.settings.base import INSTALLED_APPS, MIDDLEWARE, REST_FRAMEWORK

# =============================================================================
# Debug
# =============================================================================

DEBUG = True

# =============================================================================
# Installed Apps — Development Extras
# =============================================================================

INSTALLED_APPS += [
    "debug_toolbar",
]

# =============================================================================
# Middleware — Development Extras
# =============================================================================

MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    *MIDDLEWARE,
]

# =============================================================================
# Debug Toolbar
# =============================================================================

INTERNAL_IPS: list[str] = [
    "127.0.0.1",
    "localhost",
]

# Support Docker internal IPs for Debug Toolbar.
import socket  # noqa: E402

hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS += [".".join(ip.split(".")[:-1] + ["1"]) for ip in ips]

# =============================================================================
# DRF — Add Browsable API for development
# =============================================================================

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (  # type: ignore[index]
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
)

# =============================================================================
# Email — Console backend for development
# =============================================================================

EMAIL_BACKEND: str = "django.core.mail.backends.console.EmailBackend"

# =============================================================================
# CORS — Allow all in development
# =============================================================================

CORS_ALLOW_ALL_ORIGINS: bool = True
