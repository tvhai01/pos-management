"""Constants and closed choices for the Product app."""

from decimal import Decimal

from django.db import models


class ProductStatus(models.TextChoices):
    """Valid lifecycle states for a product."""

    ACTIVE = "active", "Đang kinh doanh"
    INACTIVE = "inactive", "Ngừng kinh doanh"


class ProductUnit(models.TextChoices):
    """Supported units of measure, stored with stable ASCII values."""

    PIECE = "piece", "Cái"
    ITEM = "item", "Chiếc"
    BOX = "box", "Hộp"
    PACK = "pack", "Gói"
    BOTTLE = "bottle", "Chai"
    CAN = "can", "Lon"
    KILOGRAM = "kg", "Kilogram (kg)"
    GRAM = "g", "Gram (g)"
    LITER = "l", "Lít (l)"
    MILLILITER = "ml", "Mililit (ml)"


MIN_PRODUCT_PRICE: Decimal = Decimal("0.01")

MSG_PRODUCT_CREATED: str = "Product created successfully."
MSG_PRODUCT_UPDATED: str = "Product updated successfully."
MSG_PRODUCT_DELETED: str = "Product deleted successfully."
MSG_PRODUCT_RESTORED: str = "Product restored successfully."
MSG_PRODUCT_NOT_FOUND: str = "Product not found."
MSG_PRODUCT_SKU_EXISTS: str = "A product with this SKU already exists."
MSG_PRODUCT_SKU_IMMUTABLE: str = "SKU cannot be changed after creation."
MSG_INVALID_PRODUCT_PRICES: str = "Selling price must be greater than cost price."

MSG_CATEGORY_CREATED: str = "Category created successfully."
MSG_CATEGORY_UPDATED: str = "Category updated successfully."
MSG_CATEGORY_DELETED: str = "Category deleted successfully."
MSG_CATEGORY_RESTORED: str = "Category restored successfully."
MSG_CATEGORY_NOT_FOUND: str = "Category not found."
MSG_CATEGORY_NAME_EXISTS: str = "A category with this name already exists."
MSG_CATEGORY_HAS_PRODUCTS: str = (
    "Category cannot be deleted while it still contains active products."
)

PRODUCT_SEARCH_FIELDS: tuple[str, ...] = ("sku", "name", "description")
PRODUCT_ORDERING_FIELDS: tuple[str, ...] = (
    "sku",
    "name",
    "cost_price",
    "selling_price",
    "status",
    "created_at",
    "updated_at",
)
CATEGORY_SEARCH_FIELDS: tuple[str, ...] = ("name", "description")
CATEGORY_ORDERING_FIELDS: tuple[str, ...] = (
    "name",
    "created_at",
    "updated_at",
)
