"""Constants and closed choices for Inventory operations."""

from django.db import models


class StockMovementType(models.TextChoices):
    """Supported reasons for changing the on-hand quantity."""

    INBOUND = "inbound", "Nhập kho"
    OUTBOUND = "outbound", "Xuất kho"
    ADJUSTMENT = "adjustment", "Điều chỉnh"


class StockStatus(models.TextChoices):
    """Computed Inventory states used by API and Dashboard clients."""

    OUT_OF_STOCK = "out_of_stock", "Hết hàng"
    LOW_STOCK = "low_stock", "Sắp hết"
    IN_STOCK = "in_stock", "Còn hàng"


DEFAULT_LOW_STOCK_THRESHOLD = "10.000"
QUANTITY_DECIMAL_PLACES = 3
QUANTITY_MAX_DIGITS = 14

INVENTORY_SEARCH_FIELDS: tuple[str, ...] = (
    "product__sku",
    "product__name",
)
INVENTORY_ORDERING_FIELDS: tuple[str, ...] = (
    "product__sku",
    "product__name",
    "quantity",
    "low_stock_threshold",
    "updated_at",
)
MOVEMENT_SEARCH_FIELDS: tuple[str, ...] = (
    "inventory__product__sku",
    "inventory__product__name",
    "reference_code",
    "note",
)
MOVEMENT_ORDERING_FIELDS: tuple[str, ...] = (
    "created_at",
    "quantity_delta",
    "balance_after",
)

MSG_MOVEMENT_CREATED = "Giao dịch kho đã được ghi nhận."
MSG_THRESHOLD_UPDATED = "Ngưỡng cảnh báo tồn kho đã được cập nhật."
MSG_INVENTORY_NOT_FOUND = "Không tìm thấy tồn kho của sản phẩm."
MSG_PRODUCT_NOT_AVAILABLE = "Sản phẩm không tồn tại hoặc đã bị xoá."
MSG_INVALID_QUANTITY = "Số lượng không hợp lệ."
MSG_INSUFFICIENT_STOCK = "Số lượng tồn kho không đủ để xuất."
MSG_NO_STOCK_CHANGE = "Số tồn điều chỉnh phải khác số tồn hiện tại."
