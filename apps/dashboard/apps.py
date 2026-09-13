"""
Django app configuration for the Dashboard app.
"""

from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """Configuration for the dashboard app.

    Session-authenticated, server-rendered admin UI: login, a module
    directory, and CRUD screens for business apps (Customer today). This
    app owns no models of its own — it's a thin presentation layer over
    the Service/Selector layers of `apps.accounts` and `apps.customers`.

    Attributes:
        default_auto_field: Uses BigAutoField globally (unused here — no models).
        name: Dotted Python path to the app.
        verbose_name: Human-readable name shown in Django admin.
    """

    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "apps.dashboard"
    verbose_name: str = "Dashboard"
