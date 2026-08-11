"""Input and output serializers for Inventory APIs."""

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.inventory.constants import (
    MSG_INVALID_QUANTITY,
    StockMovementType,
)
from apps.inventory.models import Inventory, StockMovement


class InventoryProductSerializer(serializers.Serializer):
    """Represent the Product fields needed by stock clients."""

    id = serializers.UUIDField(read_only=True)
    sku = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    unit = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    category_id = serializers.UUIDField(read_only=True, allow_null=True)


class InventorySerializer(serializers.ModelSerializer):
    """Represent one current Product balance."""

    product = InventoryProductSerializer(read_only=True)
    stock_status = serializers.CharField(read_only=True)
    updated_by = serializers.SerializerMethodField()

    class Meta:
        model = Inventory
        fields: tuple[str, ...] = (
            "id",
            "product",
            "quantity",
            "low_stock_threshold",
            "stock_status",
            "updated_by",
            "updated_at",
        )

    def get_updated_by(self, obj: Inventory) -> str | None:
        """Return the last actor email when available."""
        return obj.updated_by.email if obj.updated_by is not None else None


class StockMovementSerializer(serializers.ModelSerializer):
    """Represent an immutable Inventory ledger row."""

    product_id = serializers.UUIDField(source="inventory.product_id", read_only=True)
    product_sku = serializers.CharField(
        source="inventory.product.sku",
        read_only=True,
    )
    product_name = serializers.CharField(
        source="inventory.product.name",
        read_only=True,
    )
    movement_type_display = serializers.CharField(
        source="get_movement_type_display",
        read_only=True,
    )
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields: tuple[str, ...] = (
            "id",
            "product_id",
            "product_sku",
            "product_name",
            "movement_type",
            "movement_type_display",
            "quantity_delta",
            "balance_before",
            "balance_after",
            "reference_code",
            "note",
            "created_by",
            "created_at",
        )

    def get_created_by(self, obj: StockMovement) -> str | None:
        """Return the actor email when available."""
        return obj.created_by.email if obj.created_by is not None else None


class CreateStockMovementSerializer(serializers.Serializer):
    """Validate an inbound, outbound or adjustment request."""

    product_id = serializers.UUIDField()
    movement_type = serializers.ChoiceField(choices=StockMovementType.choices)
    quantity = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        min_value=Decimal("0"),
    )
    reference_code = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
    )
    note = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Require positive quantities except for zero-target adjustments."""
        if (
            attrs["movement_type"] != StockMovementType.ADJUSTMENT
            and attrs["quantity"] <= 0
        ):
            raise serializers.ValidationError({"quantity": MSG_INVALID_QUANTITY})
        return attrs


class UpdateThresholdSerializer(serializers.Serializer):
    """Validate a non-negative low-stock threshold."""

    low_stock_threshold = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        min_value=Decimal("0"),
    )
