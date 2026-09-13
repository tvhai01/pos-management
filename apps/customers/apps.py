"""
Django app configuration for the Customers app.
"""

from django.apps import AppConfig


class CustomersConfig(AppConfig):
    """Configuration for the customers app.

    Attributes:
        default_auto_field: Uses BigAutoField globally, but our models
            override this with UUIDField primary keys.
        name: Dotted Python path to the app.
        verbose_name: Human-readable name shown in Django admin.
    """

    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "apps.customers"
    verbose_name: str = "Customers"
