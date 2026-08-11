"""
Django app configuration for the Product app.
"""

from django.apps import AppConfig


class ProductConfig(AppConfig):
    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "apps.product"
    verbose_name: str = "Product"

    """Configuration for the product app.
    Attributes:
        default_auto_field: Uses BigAutoField globally, but our models
            override this with UUIDField primary keys.
        name: Dotted Python path to the app.
        verbose_name: Human-readable name shown in Django admin.
    """
