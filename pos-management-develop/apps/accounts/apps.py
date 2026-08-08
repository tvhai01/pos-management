"""
Django app configuration for the Accounts app.
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration for the accounts app.

    Attributes:
        default_auto_field: Uses BigAutoField globally, but our models
            override this with UUIDField primary keys.
        name: Dotted Python path to the app.
        verbose_name: Human-readable name shown in Django admin.
    """

    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "apps.accounts"
    verbose_name: str = "Accounts"
