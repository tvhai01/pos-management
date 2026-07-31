"""
Django production settings for POS Management System.

Extends base settings with production-specific security hardening.
All sensitive values MUST come from environment variables.
"""

from config.settings.base import *  # noqa: F401, F403

# =============================================================================
# Debug — NEVER True in production
# =============================================================================

DEBUG = False

# =============================================================================
# Security
# =============================================================================

# HTTPS settings
SECURE_SSL_REDIRECT: bool = True
SECURE_PROXY_SSL_HEADER: tuple[str, str] = ("HTTP_X_FORWARDED_PROTO", "https")

# HSTS — HTTP Strict Transport Security
SECURE_HSTS_SECONDS: int = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS: bool = True
SECURE_HSTS_PRELOAD: bool = True

# Cookie security
SESSION_COOKIE_SECURE: bool = True
CSRF_COOKIE_SECURE: bool = True
SESSION_COOKIE_HTTPONLY: bool = True
CSRF_COOKIE_HTTPONLY: bool = True

# Content Security
SECURE_CONTENT_TYPE_NOSNIFF: bool = True
X_FRAME_OPTIONS: str = "DENY"

# =============================================================================
# Logging — Production overrides
# =============================================================================

LOGGING_LEVEL: str = "WARNING"
