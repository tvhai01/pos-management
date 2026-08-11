"""Application exceptions raised by Inventory business rules."""

from rest_framework import status

from apps.inventory.constants import (
    MSG_INSUFFICIENT_STOCK,
    MSG_INVALID_QUANTITY,
    MSG_INVENTORY_NOT_FOUND,
    MSG_NO_STOCK_CHANGE,
    MSG_PRODUCT_NOT_AVAILABLE,
)
from shared.exceptions import ApplicationError


class InventoryNotFoundError(ApplicationError):
    """Raised when no Inventory exists for the requested Product."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = MSG_INVENTORY_NOT_FOUND
    default_code = "inventory_not_found"


class InventoryProductNotFoundError(ApplicationError):
    """Raised when a Product cannot accept Inventory operations."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = MSG_PRODUCT_NOT_AVAILABLE
    default_code = "inventory_product_not_found"


class InvalidStockQuantityError(ApplicationError):
    """Raised when a quantity violates Inventory rules."""

    default_detail = MSG_INVALID_QUANTITY
    default_code = "invalid_stock_quantity"


class InsufficientStockError(ApplicationError):
    """Raised when an outbound movement would make stock negative."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = MSG_INSUFFICIENT_STOCK
    default_code = "insufficient_stock"


class NoStockChangeError(ApplicationError):
    """Raised when an adjustment targets the current balance."""

    default_detail = MSG_NO_STOCK_CHANGE
    default_code = "no_stock_change"
