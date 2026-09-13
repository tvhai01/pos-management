"""REST API URL configuration for Inventory."""

from django.urls import path

from apps.inventory.views import (
    InventoryDetailView,
    InventoryListView,
    InventoryThresholdUpdateView,
    StockMovementListCreateView,
)

app_name = "inventory"

urlpatterns = [
    path("inventory/", InventoryListView.as_view(), name="inventory-list"),
    path(
        "inventory/movements/",
        StockMovementListCreateView.as_view(),
        name="movement-list-create",
    ),
    path(
        "inventory/<uuid:product_id>/",
        InventoryDetailView.as_view(),
        name="inventory-detail",
    ),
    path(
        "inventory/<uuid:product_id>/threshold/",
        InventoryThresholdUpdateView.as_view(),
        name="inventory-threshold",
    ),
]
