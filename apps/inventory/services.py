"""Transactional business operations for Inventory quantities."""

import logging
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.models import User
from apps.inventory.constants import StockMovementType
from apps.inventory.exceptions import (
    InsufficientStockError,
    InvalidStockQuantityError,
    InventoryProductNotFoundError,
    NoStockChangeError,
)
from apps.inventory.models import Inventory, StockMovement
from apps.inventory.validators import parse_quantity
from apps.product.models import Product

logger = logging.getLogger(__name__)


class InventoryService:
    """Create balances and serialize all stock mutations."""

    @staticmethod
    @transaction.atomic
    def initialize_inventory(
        product: Product,
        created_by: User | None = None,
    ) -> Inventory:
        """Ensure a Product has one zero-balance Inventory record."""
        inventory, _ = Inventory.objects.get_or_create(
            product=product,
            defaults={"created_by": created_by, "updated_by": created_by},
        )
        return inventory

    @staticmethod
    def _lock_inventory(
        product_id: UUID | str,
        actor: User | None,
    ) -> Inventory:
        """Lock the Product first, then retrieve/create and lock its balance."""
        try:
            product = Product.all_objects.select_for_update().get(
                id=product_id,
                is_deleted=False,
            )
        except (Product.DoesNotExist, ValidationError, ValueError, TypeError) as exc:
            raise InventoryProductNotFoundError() from exc

        inventory, _ = Inventory.objects.get_or_create(
            product=product,
            defaults={"created_by": actor, "updated_by": actor},
        )
        return Inventory.objects.select_for_update().get(id=inventory.id)

    @staticmethod
    @transaction.atomic
    def record_movement(
        product_id: UUID | str,
        movement_type: str,
        quantity: Any,
        reference_code: str = "",
        note: str = "",
        created_by: User | None = None,
    ) -> tuple[Inventory, StockMovement]:
        """Atomically apply one movement and append its immutable ledger row."""
        allow_zero = movement_type == StockMovementType.ADJUSTMENT
        normalized_quantity = parse_quantity(quantity, allow_zero=allow_zero)
        if normalized_quantity is None:
            raise InvalidStockQuantityError()
        if movement_type not in StockMovementType.values:
            raise InvalidStockQuantityError()

        inventory = InventoryService._lock_inventory(product_id, created_by)
        balance_before = inventory.quantity

        if movement_type == StockMovementType.INBOUND:
            quantity_delta = normalized_quantity
            balance_after = balance_before + quantity_delta
        elif movement_type == StockMovementType.OUTBOUND:
            quantity_delta = -normalized_quantity
            balance_after = balance_before + quantity_delta
            if balance_after < 0:
                raise InsufficientStockError()
        else:
            balance_after = normalized_quantity
            quantity_delta = balance_after - balance_before
            if quantity_delta == 0:
                raise NoStockChangeError()

        inventory.quantity = balance_after
        inventory.updated_by = created_by
        inventory.save(update_fields=["quantity", "updated_by", "updated_at"])

        movement = StockMovement.objects.create(
            inventory=inventory,
            movement_type=movement_type,
            quantity_delta=quantity_delta,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_code=reference_code.strip(),
            note=note.strip(),
            created_by=created_by,
            updated_by=created_by,
        )
        logger.info(
            "Stock movement created: product=%s type=%s delta=%s balance=%s",
            inventory.product_id,
            movement_type,
            quantity_delta,
            balance_after,
        )
        return inventory, movement

    @staticmethod
    @transaction.atomic
    def update_low_stock_threshold(
        product_id: UUID | str,
        threshold: Any,
        updated_by: User | None = None,
    ) -> Inventory:
        """Update a Product warning threshold under the same row lock."""
        normalized_threshold = parse_quantity(threshold, allow_zero=True)
        if normalized_threshold is None:
            raise InvalidStockQuantityError()
        inventory = InventoryService._lock_inventory(product_id, updated_by)
        inventory.low_stock_threshold = normalized_threshold
        inventory.updated_by = updated_by
        inventory.save(
            update_fields=["low_stock_threshold", "updated_by", "updated_at"]
        )
        return inventory
