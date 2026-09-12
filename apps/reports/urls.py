"""REST API URL configuration for Report."""

from django.urls import path

from apps.reports.views import (
    CustomerReportExportView,
    CustomerReportView,
    InventoryReportExportView,
    InventoryReportView,
    PaymentBreakdownExportView,
    PaymentBreakdownReportView,
    RevenueReportExportView,
    RevenueReportView,
    TopSellingProductsExportView,
    TopSellingProductsReportView,
)

app_name = "reports"

urlpatterns = [
    path("reports/revenue/", RevenueReportView.as_view(), name="revenue"),
    path(
        "reports/revenue/export/",
        RevenueReportExportView.as_view(),
        name="revenue-export",
    ),
    path(
        "reports/products/top-selling/",
        TopSellingProductsReportView.as_view(),
        name="top-selling-products",
    ),
    path(
        "reports/products/top-selling/export/",
        TopSellingProductsExportView.as_view(),
        name="top-selling-products-export",
    ),
    path("reports/inventory/", InventoryReportView.as_view(), name="inventory"),
    path(
        "reports/inventory/export/",
        InventoryReportExportView.as_view(),
        name="inventory-export",
    ),
    path(
        "reports/payments/breakdown/",
        PaymentBreakdownReportView.as_view(),
        name="payment-breakdown",
    ),
    path(
        "reports/payments/breakdown/export/",
        PaymentBreakdownExportView.as_view(),
        name="payment-breakdown-export",
    ),
    path("reports/customers/", CustomerReportView.as_view(), name="customers"),
    path(
        "reports/customers/export/",
        CustomerReportExportView.as_view(),
        name="customers-export",
    ),
]
