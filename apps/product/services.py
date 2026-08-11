"""Transactional business operations for Product and Category."""

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import transaction

from apps.accounts.models import User
from apps.product.constants import ProductStatus, ProductUnit
from apps.product.exceptions import (
    CategoryHasProductsError,
    CategoryNotFoundError,
    ProductNotFoundError,
)
from apps.product.models import Category, Product
from apps.product.selectors import CategorySelector, ProductSelector
from apps.product.validators import normalize_category_name, normalize_sku

logger = logging.getLogger(__name__)

_PRODUCT_UPDATABLE_FIELDS: set[str] = {
    "name",
    "description",
    "category",
    "unit",
    "image",
    "cost_price",
    "selling_price",
    "status",
}
_CATEGORY_UPDATABLE_FIELDS: set[str] = {"name", "description"}


class CategoryService:
    """Business operations for categories."""

    @staticmethod
    @transaction.atomic
    def create_category(
        name: str,
        description: str = "",
        created_by: User | None = None,
    ) -> Category:
        """Create a category with audit information."""
        category = Category.objects.create(
            name=normalize_category_name(name),
            description=description,
            created_by=created_by,
            updated_by=created_by,
        )
        logger.info("Category created: %s", category.name)
        return category

    @staticmethod
    @transaction.atomic
    def update_category(
        category_id: UUID | str,
        updated_by: User | None = None,
        **kwargs: Any,
    ) -> Category:
        """Update allowed category fields or raise when not found."""
        category = CategorySelector.get_category_by_id(category_id)
        if category is None:
            raise CategoryNotFoundError()

        update_fields: list[str] = []
        for field, value in kwargs.items():
            if field in _CATEGORY_UPDATABLE_FIELDS and value is not None:
                if field == "name":
                    value = normalize_category_name(value)
                setattr(category, field, value)
                update_fields.append(field)
        if update_fields:
            category.updated_by = updated_by
            update_fields.extend(["updated_by", "updated_at"])
            category.save(update_fields=update_fields)
        return category

    @staticmethod
    @transaction.atomic
    def delete_category(
        category_id: UUID | str, deleted_by: User | None = None
    ) -> None:
        """Soft-delete an empty category while preserving its row."""
        category = CategorySelector.get_category_by_id(category_id)
        if category is None:
            raise CategoryNotFoundError()
        if CategorySelector.has_active_products(category.id):
            raise CategoryHasProductsError()
        category.soft_delete()
        category.updated_by = deleted_by
        category.save(
            update_fields=["is_deleted", "deleted_at", "updated_by", "updated_at"]
        )

    @staticmethod
    @transaction.atomic
    def restore_category(
        category_id: UUID | str, restored_by: User | None = None
    ) -> Category:
        """Restore a previously soft-deleted category."""
        category = CategorySelector.get_deleted_category_by_id(category_id)
        if category is None:
            raise CategoryNotFoundError()
        category.is_deleted = False
        category.deleted_at = None
        category.updated_by = restored_by
        category.save(
            update_fields=["is_deleted", "deleted_at", "updated_by", "updated_at"]
        )
        return category


class ProductService:
    """Business operations for products."""

    @staticmethod
    @transaction.atomic
    def create_product(
        sku: str,
        name: str,
        cost_price: Decimal,
        selling_price: Decimal,
        description: str = "",
        category_id: UUID | str | None = None,
        unit: str = ProductUnit.PIECE,
        image: Any = None,
        status: str = ProductStatus.ACTIVE,
        created_by: User | None = None,
    ) -> Product:
        """Create a product with an immutable normalized SKU."""
        category = None
        if category_id:
            category = CategorySelector.get_category_by_id(category_id)
            if category is None:
                raise CategoryNotFoundError()
        product = Product.objects.create(
            sku=normalize_sku(sku),
            name=name.strip(),
            description=description,
            category=category,
            unit=unit,
            image=image,
            cost_price=cost_price,
            selling_price=selling_price,
            status=status,
            created_by=created_by,
            updated_by=created_by,
        )

        # Give every Product a stable zero-balance row. Inventory remains the
        # sole owner of later quantity mutations.
        from apps.inventory.services import InventoryService

        InventoryService.initialize_inventory(product, created_by=created_by)
        logger.info("Product created: %s", product.sku)
        return product

    @staticmethod
    @transaction.atomic
    def update_product(
        product_id: UUID | str,
        updated_by: User | None = None,
        **kwargs: Any,
    ) -> Product:
        """Update mutable product fields while preserving the SKU."""
        product = ProductSelector.get_product_by_id(product_id)
        if product is None:
            raise ProductNotFoundError()

        if "category_id" in kwargs:
            category_id = kwargs.pop("category_id")
            if category_id:
                category = CategorySelector.get_category_by_id(category_id)
                if category is None:
                    raise CategoryNotFoundError()
                kwargs["category"] = category
            else:
                kwargs["category"] = None

        update_fields: list[str] = []
        for field, value in kwargs.items():
            if field in _PRODUCT_UPDATABLE_FIELDS and (
                value is not None or field in {"category", "image"}
            ):
                if field == "name":
                    value = value.strip()
                setattr(product, field, value)
                update_fields.append(field)
        if update_fields:
            product.updated_by = updated_by
            update_fields.extend(["updated_by", "updated_at"])
            product.save(update_fields=update_fields)
        return product

    @staticmethod
    @transaction.atomic
    def delete_product(product_id: UUID | str, deleted_by: User | None = None) -> None:
        """Soft-delete a product so inventory history remains valid."""
        product = ProductSelector.get_product_by_id(product_id)
        if product is None:
            raise ProductNotFoundError()
        product.soft_delete()
        product.updated_by = deleted_by
        product.save(
            update_fields=["is_deleted", "deleted_at", "updated_by", "updated_at"]
        )

    @staticmethod
    @transaction.atomic
    def restore_product(
        product_id: UUID | str, restored_by: User | None = None
    ) -> Product:
        """Restore a previously soft-deleted product."""
        product = ProductSelector.get_deleted_product_by_id(product_id)
        if product is None:
            raise ProductNotFoundError()
        if (
            product.category_id
            and CategorySelector.get_category_by_id(product.category_id) is None
        ):
            raise CategoryNotFoundError()
        product.is_deleted = False
        product.deleted_at = None
        product.updated_by = restored_by
        product.save(
            update_fields=["is_deleted", "deleted_at", "updated_by", "updated_at"]
        )
        return product
