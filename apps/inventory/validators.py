"""Decimal-safe Inventory input normalization."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from apps.inventory.constants import QUANTITY_DECIMAL_PLACES

_QUANTITY_STEP = Decimal("1").scaleb(-QUANTITY_DECIMAL_PLACES)


def parse_quantity(value: Any, *, allow_zero: bool = False) -> Decimal | None:
    """Parse a finite quantity and normalize it to the supported precision."""
    try:
        quantity = Decimal(str(value)).quantize(_QUANTITY_STEP, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not quantity.is_finite():
        return None
    if quantity < 0 or (quantity == 0 and not allow_zero):
        return None
    return quantity
