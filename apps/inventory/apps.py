"""Django application configuration for Inventory."""

from django.apps import AppConfig


class InventoryConfig(AppConfig):
    """Configure the Inventory application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.inventory"
    verbose_name = "Quản lý kho"
