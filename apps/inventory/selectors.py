"""Read-only queries for Inventory balances and movement history."""

from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import F, Q, QuerySet

from apps.inventory.models import Inventory, StockMovement


class InventorySelector:
    """Read-only Inventory queries."""

    @staticmethod
    def get_all_inventories() -> QuerySet[Inventory]:
        """Return active Product balances for API filtering/pagination."""
        return Inventory.objects.filter(product__is_deleted=False).select_related(
            "product", "product__category", "created_by", "updated_by"
        )

    @staticmethod
    def get_inventory_by_product_id(
        product_id: UUID | str,
        *,
        include_deleted_product: bool = False,
    ) -> Inventory | None:
        """Retrieve one balance by Product UUID."""
        queryset = Inventory.objects.select_related("product", "product__category")
        if not include_deleted_product:
            queryset = queryset.filter(product__is_deleted=False)
        try:
            return queryset.get(product_id=product_id)
        except (Inventory.DoesNotExist, ValidationError, ValueError, TypeError):
            return None

    @staticmethod
    def search_inventories(
        search: str = "",
        category_id: str = "",
        product_status: str = "",
        stock_status: str = "",
    ) -> QuerySet[Inventory]:
        """Filter balances for the server-rendered Dashboard."""
        queryset = InventorySelector.get_all_inventories()
        if search:
            queryset = queryset.filter(
                Q(product__sku__icontains=search) | Q(product__name__icontains=search)
            )
        if category_id:
            queryset = queryset.filter(product__category_id=category_id)
        if product_status:
            queryset = queryset.filter(product__status=product_status)
        if stock_status == "out_of_stock":
            queryset = queryset.filter(quantity=0)
        elif stock_status == "low_stock":
            queryset = queryset.filter(
                quantity__gt=0,
                quantity__lte=F("low_stock_threshold"),
            )
        elif stock_status == "in_stock":
            queryset = queryset.filter(quantity__gt=F("low_stock_threshold"))
        return queryset.order_by("product__sku")


class StockMovementSelector:
    """Read-only StockMovement queries."""

    @staticmethod
    def get_all_movements() -> QuerySet[StockMovement]:
        """Return ledger rows with Product and actor data preloaded."""
        return StockMovement.objects.select_related(
            "inventory",
            "inventory__product",
            "created_by",
        )

    @staticmethod
    def get_product_movements(product_id: UUID | str) -> QuerySet[StockMovement]:
        """Return newest-first history for one Product."""
        return StockMovementSelector.get_all_movements().filter(
            inventory__product_id=product_id
        )
