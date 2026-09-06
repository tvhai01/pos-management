"""Read-only query layer for Product and Category data."""

from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import Count, Q, QuerySet
from django.db.models.expressions import OrderBy
from django.db.models.functions import Lower

from apps.product.models import Category, Product


class CategorySelector:
    """Read-only queries for Category records."""

    @staticmethod
    def get_category_by_id(category_id: UUID | str) -> Category | None:
        """Return a live category by UUID, or None when unavailable."""
        try:
            return Category.objects.get(id=category_id)
        except (Category.DoesNotExist, ValidationError, ValueError, TypeError):
            return None

    @staticmethod
    def get_deleted_category_by_id(category_id: UUID | str) -> Category | None:
        """Return a deleted category by UUID, or None when unavailable."""
        try:
            return Category.all_objects.get(id=category_id, is_deleted=True)
        except (Category.DoesNotExist, ValidationError, ValueError, TypeError):
            return None

    @staticmethod
    def get_all_categories() -> QuerySet[Category]:
        """Return live categories for API filtering and form choices."""
        return Category.objects.select_related("created_by", "updated_by").all()

    @staticmethod
    def get_deleted_categories() -> QuerySet[Category]:
        """Return deleted categories for the audit/trash screen."""
        return Category.all_objects.filter(is_deleted=True).select_related(
            "created_by", "updated_by"
        )

    @staticmethod
    def search_categories(
        search: str = "", has_products: str = "", sort: str = ""
    ) -> QuerySet[Category]:
        """Filter and order categories for the server-rendered dashboard."""
        queryset = Category.objects.select_related("created_by", "updated_by").annotate(
            active_product_count=Count(
                "products",
                filter=Q(products__is_deleted=False),
            )
        )
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        if has_products == "yes":
            queryset = queryset.filter(active_product_count__gt=0)
        elif has_products == "no":
            queryset = queryset.filter(active_product_count=0)

        ordering_map: dict[str, str | OrderBy] = {
            "name_asc": Lower("name").asc(),
            "name_desc": Lower("name").desc(),
            "most_products": "-active_product_count",
            "newest": "-created_at",
            "oldest": "created_at",
        }
        return queryset.order_by(ordering_map.get(sort, Lower("name").asc()))

    @staticmethod
    def name_exists(name: str, exclude_id: UUID | str | None = None) -> bool:
        """Check case-insensitive uniqueness across live and deleted rows."""
        queryset = Category.all_objects.filter(name__iexact=name)
        if exclude_id is not None:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()

    @staticmethod
    def has_active_products(category_id: UUID | str) -> bool:
        """Return whether a category still contains a live product."""
        return Product.objects.filter(category_id=category_id).exists()


class ProductSelector:
    """Read-only queries for Product records."""

    @staticmethod
    def get_product_by_id(product_id: UUID | str) -> Product | None:
        """Return a live product by UUID, or None when unavailable."""
        try:
            return Product.objects.select_related(
                "category", "created_by", "updated_by"
            ).get(id=product_id)
        except (Product.DoesNotExist, ValidationError, ValueError, TypeError):
            return None

    @staticmethod
    def get_deleted_product_by_id(product_id: UUID | str) -> Product | None:
        """Return a deleted product by UUID, or None when unavailable."""
        try:
            return Product.all_objects.select_related(
                "category", "created_by", "updated_by"
            ).get(id=product_id, is_deleted=True)
        except (Product.DoesNotExist, ValidationError, ValueError, TypeError):
            return None

    @staticmethod
    def get_all_products() -> QuerySet[Product]:
        """Return live products with relationships needed by list serializers."""
        return Product.objects.select_related(
            "category", "created_by", "updated_by"
        ).all()

    @staticmethod
    def get_sellable_product_for_update(product_id: UUID | str) -> Product | None:
        """Lock one active, non-deleted Product for order price snapshots."""
        try:
            return Product.objects.select_for_update().get(
                id=product_id,
                status="active",
                is_deleted=False,
            )
        except (Product.DoesNotExist, ValidationError, ValueError, TypeError):
            return None

    @staticmethod
    def get_deleted_products() -> QuerySet[Product]:
        """Return deleted products for the audit/trash screen."""
        return Product.all_objects.filter(is_deleted=True).select_related(
            "category", "created_by", "updated_by"
        )

    @staticmethod
    def search_products(
        search: str = "",
        category_id: str = "",
        status: str = "",
        sort: str = "",
    ) -> QuerySet[Product]:
        """Filter and order products for the server-rendered dashboard."""
        queryset = ProductSelector.get_all_products()
        if search:
            queryset = queryset.filter(
                Q(sku__icontains=search)
                | Q(name__icontains=search)
                | Q(description__icontains=search)
            )
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if status:
            queryset = queryset.filter(status=status)

        ordering_map: dict[str, str | OrderBy] = {
            "name_asc": Lower("name").asc(),
            "name_desc": Lower("name").desc(),
            "oldest": "created_at",
            "price_asc": "selling_price",
            "price_desc": "-selling_price",
        }
        return queryset.order_by(ordering_map.get(sort, "-created_at"))

    @staticmethod
    def sku_exists(sku: str, exclude_id: UUID | str | None = None) -> bool:
        """Check case-insensitive SKU uniqueness across all rows."""
        queryset = Product.all_objects.filter(sku__iexact=sku)
        if exclude_id is not None:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()
