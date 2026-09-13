"""Read-focused Django Admin views for Inventory audit data."""

from django.contrib import admin

from apps.inventory.models import Inventory, StockMovement


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    """Expose balances for audit without direct quantity editing."""

    list_display = (
        "product",
        "quantity",
        "low_stock_threshold",
        "stock_status",
        "updated_by",
        "updated_at",
    )
    search_fields = ("product__sku", "product__name")
    list_filter = ("product__status", "product__category")
    readonly_fields = (
        "id",
        "product",
        "quantity",
        "low_stock_threshold",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request) -> bool:
        """Inventory rows are initialized by the Service layer."""
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        """Balances must never be deleted."""
        return False


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    """Expose the immutable movement ledger for audit."""

    list_display = (
        "inventory",
        "movement_type",
        "quantity_delta",
        "balance_before",
        "balance_after",
        "reference_code",
        "created_by",
        "created_at",
    )
    search_fields = (
        "inventory__product__sku",
        "inventory__product__name",
        "reference_code",
    )
    list_filter = ("movement_type", "created_at")

    def has_add_permission(self, request) -> bool:
        """Movements can only be created by Inventory Service."""
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        """Ledger rows are immutable."""
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        """Ledger rows cannot be deleted."""
        return False
