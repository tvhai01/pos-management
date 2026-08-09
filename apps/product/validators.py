"""Validation helpers shared by Product API serializers and HTML forms."""

from decimal import Decimal, InvalidOperation

from apps.product.constants import MIN_PRODUCT_PRICE


def normalize_sku(value: str) -> str:
    """Normalize a SKU for consistent case-insensitive uniqueness checks."""
    return value.strip().upper()


def normalize_category_name(value: str) -> str:
    """Trim redundant surrounding whitespace from a category name."""
    return value.strip()


def parse_price(value: object) -> Decimal | None:
    """Parse a user-entered price, accepting comma grouping separators.

    Args:
        value: Raw form or serializer value.

    Returns:
        A positive Decimal, or None when the input is invalid.
    """
    normalized = str(value).replace(",", "").strip()
    try:
        price = Decimal(normalized)
    except (InvalidOperation, TypeError, ValueError):
        return None
    return price if price >= MIN_PRODUCT_PRICE else None


def has_valid_price_relationship(cost_price: Decimal, selling_price: Decimal) -> bool:
    """Return whether both prices are positive and selling exceeds cost."""
    return (
        cost_price >= MIN_PRODUCT_PRICE
        and selling_price >= MIN_PRODUCT_PRICE
        and selling_price > cost_price
    )
