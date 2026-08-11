"""Current stock balances and immutable Inventory ledger entries."""

from decimal import Decimal
from typing import Any, ClassVar

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.inventory.constants import (
    DEFAULT_LOW_STOCK_THRESHOLD,
    QUANTITY_DECIMAL_PLACES,
    QUANTITY_MAX_DIGITS,
    StockMovementType,
    StockStatus,
)
from apps.product.models import Product
from shared.base_model import AuditModel


class Inventory(AuditModel):
    """The current on-hand quantity for one Product."""

    product = models.OneToOneField(
        Product,
        on_delete=models.PROTECT,
        related_name="inventory_record",
        verbose_name="Sản phẩm",
    )
    quantity = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        default=Decimal("0"),
        verbose_name="Số lượng tồn",
    )
    low_stock_threshold = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        default=Decimal(DEFAULT_LOW_STOCK_THRESHOLD),
        verbose_name="Ngưỡng tồn thấp",
    )

    class Meta(AuditModel.Meta):
        db_table = "inventory_inventory"
        verbose_name = "Tồn kho"
        verbose_name_plural = "Tồn kho"
        ordering = ["product__sku"]  # noqa: RUF012 - Django Meta expects a list
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=["quantity"], name="idx_inventory_quantity"),
        )
        constraints: ClassVar[tuple[models.BaseConstraint, ...]] = (
            models.CheckConstraint(
                condition=Q(quantity__gte=0),
                name="inventory_quantity_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(low_stock_threshold__gte=0),
                name="inventory_threshold_nonnegative",
            ),
        )

    @property
    def stock_status(self) -> str:
        """Return the computed stock warning state."""
        if self.quantity == 0:
            return StockStatus.OUT_OF_STOCK
        if self.quantity <= self.low_stock_threshold:
            return StockStatus.LOW_STOCK
        return StockStatus.IN_STOCK

    @property
    def stock_status_label(self) -> str:
        """Return the localized label for the computed stock state."""
        return StockStatus(self.stock_status).label

    def __str__(self) -> str:
        """Return a readable Product balance."""
        return f"{self.product.sku}: {self.quantity:.3f}"


class StockMovement(AuditModel):
    """An immutable ledger row recording one stock balance transition."""

    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.PROTECT,
        related_name="movements",
        verbose_name="Tồn kho",
    )
    movement_type = models.CharField(
        max_length=20,
        choices=StockMovementType.choices,
        verbose_name="Loại giao dịch",
    )
    quantity_delta = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        verbose_name="Số lượng thay đổi",
    )
    balance_before = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        verbose_name="Tồn trước giao dịch",
    )
    balance_after = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS,
        decimal_places=QUANTITY_DECIMAL_PLACES,
        verbose_name="Tồn sau giao dịch",
    )
    reference_code = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Mã tham chiếu",
    )
    note = models.TextField(blank=True, default="", verbose_name="Ghi chú")

    class Meta(AuditModel.Meta):
        db_table = "inventory_stock_movement"
        verbose_name = "Biến động kho"
        verbose_name_plural = "Biến động kho"
        ordering = ["-created_at"]  # noqa: RUF012 - Django Meta expects a list
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=["movement_type"], name="idx_movement_type"),
            models.Index(fields=["created_at"], name="idx_movement_created"),
        )
        constraints: ClassVar[tuple[models.BaseConstraint, ...]] = (
            models.CheckConstraint(
                condition=~Q(quantity_delta=0),
                name="movement_delta_nonzero",
            ),
            models.CheckConstraint(
                condition=Q(balance_before__gte=0) & Q(balance_after__gte=0),
                name="movement_balances_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        movement_type=StockMovementType.INBOUND,
                        quantity_delta__gt=0,
                    )
                    | Q(
                        movement_type=StockMovementType.OUTBOUND,
                        quantity_delta__lt=0,
                    )
                    | (
                        Q(movement_type=StockMovementType.ADJUSTMENT)
                        & ~Q(quantity_delta=0)
                    )
                ),
                name="movement_delta_matches_type",
            ),
        )

    def __str__(self) -> str:
        """Return the Product, movement type and signed delta."""
        return (
            f"{self.inventory.product.sku} "
            f"{self.get_movement_type_display()}: {self.quantity_delta:+}"
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Prevent modification after a ledger entry has been created."""
        if not self._state.adding:
            raise ValidationError("StockMovement records are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        """Prevent deletion of Inventory history."""
        raise ValidationError("StockMovement records cannot be deleted.")
