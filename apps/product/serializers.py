"""Input validation and output formatting for Product and Category APIs."""

from typing import Any
from uuid import UUID

from rest_framework import serializers

from apps.product.constants import (
    MIN_PRODUCT_PRICE,
    MSG_CATEGORY_NAME_EXISTS,
    MSG_INVALID_PRODUCT_PRICES,
    MSG_PRODUCT_SKU_EXISTS,
    MSG_PRODUCT_SKU_IMMUTABLE,
    ProductStatus,
    ProductUnit,
)
from apps.product.models import Category, Product
from apps.product.selectors import CategorySelector, ProductSelector
from apps.product.validators import (
    has_valid_price_relationship,
    normalize_category_name,
    normalize_sku,
)


class CategorySummarySerializer(serializers.ModelSerializer):
    """Serialize the category fields embedded in a Product response."""

    class Meta:
        model = Category
        fields: tuple[str, ...] = ("id", "name")


class CategoryDetailSerializer(serializers.ModelSerializer):
    """Serialize complete category details including audit information."""

    created_by = serializers.SerializerMethodField()
    updated_by = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields: tuple[str, ...] = (
            "id",
            "name",
            "description",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )

    def get_created_by(self, obj: Category) -> str | None:
        """Return the creator email when available."""
        return obj.created_by.email if obj.created_by is not None else None

    def get_updated_by(self, obj: Category) -> str | None:
        """Return the last editor email when available."""
        return obj.updated_by.email if obj.updated_by is not None else None


class CreateCategorySerializer(serializers.Serializer):
    """Validate input for creating a category."""

    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_name(self, value: str) -> str:
        """Normalize and validate category name uniqueness."""
        value = normalize_category_name(value)
        if CategorySelector.name_exists(value):
            raise serializers.ValidationError(MSG_CATEGORY_NAME_EXISTS)
        return value


class UpdateCategorySerializer(serializers.Serializer):
    """Validate partial category updates."""

    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)

    def validate_name(self, value: str) -> str:
        """Validate name uniqueness while excluding the current category."""
        value = normalize_category_name(value)
        category_id: UUID | str | None = self.context.get("category_id")
        if CategorySelector.name_exists(value, exclude_id=category_id):
            raise serializers.ValidationError(MSG_CATEGORY_NAME_EXISTS)
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Require at least one field for an update."""
        if not attrs:
            raise serializers.ValidationError(
                "At least one field must be provided to update the category."
            )
        return attrs


class ProductListSerializer(serializers.ModelSerializer):
    """Serialize lightweight product rows for paginated lists."""

    category = CategorySummarySerializer(read_only=True)
    unit_display = serializers.CharField(source="get_unit_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Product
        fields: tuple[str, ...] = (
            "id",
            "sku",
            "name",
            "category",
            "unit",
            "unit_display",
            "cost_price",
            "selling_price",
            "status",
            "status_display",
            "created_at",
        )


class ProductDetailSerializer(ProductListSerializer):
    """Serialize complete product details including audit fields."""

    created_by = serializers.SerializerMethodField()
    updated_by = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields: tuple[str, ...] = (
            *ProductListSerializer.Meta.fields,
            "description",
            "image",
            "created_by",
            "updated_by",
            "updated_at",
        )

    def get_created_by(self, obj: Product) -> str | None:
        """Return the creator email when available."""
        return obj.created_by.email if obj.created_by is not None else None

    def get_updated_by(self, obj: Product) -> str | None:
        """Return the last editor email when available."""
        return obj.updated_by.email if obj.updated_by is not None else None


class ProductPriceValidationMixin:
    """Share price relationship validation between create and update inputs."""

    def validate_price_relationship(
        self,
        attrs: dict[str, Any],
        product: Product | None = None,
    ) -> dict[str, Any]:
        """Ensure positive prices and selling price greater than cost."""
        cost_price = attrs.get(
            "cost_price", product.cost_price if product is not None else None
        )
        selling_price = attrs.get(
            "selling_price", product.selling_price if product is not None else None
        )
        if cost_price is None or selling_price is None:
            return attrs
        if not has_valid_price_relationship(cost_price, selling_price):
            raise serializers.ValidationError(
                {"selling_price": MSG_INVALID_PRODUCT_PRICES}
            )
        return attrs


class CreateProductSerializer(ProductPriceValidationMixin, serializers.Serializer):
    """Validate input for creating a product."""

    sku = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    category_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    unit = serializers.ChoiceField(
        choices=ProductUnit.choices,
        required=False,
        default=ProductUnit.PIECE,
    )
    image = serializers.ImageField(required=False, allow_null=True, default=None)
    cost_price = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=MIN_PRODUCT_PRICE,
    )
    selling_price = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=MIN_PRODUCT_PRICE,
    )
    status = serializers.ChoiceField(
        choices=ProductStatus.choices,
        required=False,
        default=ProductStatus.ACTIVE,
    )

    def validate_sku(self, value: str) -> str:
        """Normalize and validate SKU uniqueness across all rows."""
        value = normalize_sku(value)
        if ProductSelector.sku_exists(value):
            raise serializers.ValidationError(MSG_PRODUCT_SKU_EXISTS)
        return value

    def validate_category_id(self, value: UUID | None) -> UUID | None:
        """Require an existing live Category when a category is supplied."""
        if value is not None and CategorySelector.get_category_by_id(value) is None:
            raise serializers.ValidationError("Category not found.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate the price relationship."""
        return self.validate_price_relationship(attrs)


class UpdateProductSerializer(ProductPriceValidationMixin, serializers.Serializer):
    """Validate mutable Product fields; SKU is deliberately immutable."""

    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    unit = serializers.ChoiceField(choices=ProductUnit.choices, required=False)
    image = serializers.ImageField(required=False, allow_null=True)
    cost_price = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=MIN_PRODUCT_PRICE,
        required=False,
    )
    selling_price = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=MIN_PRODUCT_PRICE,
        required=False,
    )
    status = serializers.ChoiceField(choices=ProductStatus.choices, required=False)

    def validate_category_id(self, value: UUID | None) -> UUID | None:
        """Require an existing live Category when a category is supplied."""
        if value is not None and CategorySelector.get_category_by_id(value) is None:
            raise serializers.ValidationError("Category not found.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Reject SKU changes, empty updates, and invalid price relationships."""
        if "sku" in self.initial_data:
            raise serializers.ValidationError({"sku": MSG_PRODUCT_SKU_IMMUTABLE})
        if not attrs:
            raise serializers.ValidationError(
                "At least one field must be provided to update the product."
            )
        product_id: UUID | str | None = self.context.get("product_id")
        product = ProductSelector.get_product_by_id(product_id) if product_id else None
        return self.validate_price_relationship(attrs, product=product)
