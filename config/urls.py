"""
URL configuration for POS Management System.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config.views import HomeView

urlpatterns: list = [
    # Home — session-authenticated dashboard UI (login + feature screens)
    path("", include("apps.dashboard.urls")),
    # Django Admin
    path("admin/", admin.site.urls),
    # API v1 — JSON root / feature directory (for API consumers, not browsers)
    path("api/v1/", HomeView.as_view(), name="api-root"),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.customers.urls")),
    path("api/v1/", include("apps.invoices.urls")),
    path("api/v1/", include("apps.orders.urls")),
    path("api/v1/", include("apps.payments.urls")),
    path("api/v1/", include("apps.product.urls")),
    path("api/v1/", include("apps.inventory.urls")),
    path("api/v1/", include("apps.reports.urls")),
]

# Debug Toolbar — only in development
if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
        *urlpatterns,
    ]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
