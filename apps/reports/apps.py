"""Django application configuration for Report."""

from django.apps import AppConfig


class ReportsConfig(AppConfig):
    """Configure the Report application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reports"
    verbose_name = "Báo cáo"
