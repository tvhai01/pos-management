"""Django Admin configuration for Product and Category audit access."""

from typing import cast

from django.contrib import admin, messages
from django.http import HttpRequest

from apps.accounts.models import User
from apps.product.exceptions import CategoryHasProductsError
from apps.product.models import Category, Product
from apps.product.services import CategoryService, ProductService


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin list for live and soft-deleted categories."""

    list_display = (
        "name",
        "is_deleted",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    )
    search_fields = ("name", "description")
    list_filter = ("is_deleted",)
    readonly_fields = (
        "id",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
        "is_deleted",
        "deleted_at",
    )

    def get_queryset(self, request: HttpRequest):
        """Include soft-deleted categories for audit purposes."""
        return Category.all_objects.select_related("created_by", "updated_by")

    def save_model(self, request, obj, form, change):
        """Populate audit users for admin writes."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def delete_model(self, request: HttpRequest, obj: Category) -> None:
        """Convert the Django Admin delete action into a soft delete."""
        try:
            CategoryService.delete_category(
                obj.id,
                deleted_by=cast(User, request.user),
            )
        except CategoryHasProductsError as exc:
            self.message_user(request, str(exc.detail), level=messages.ERROR)

    def delete_queryset(self, request: HttpRequest, queryset) -> None:
        """Soft-delete every eligible selected category."""
        for category in queryset.filter(is_deleted=False):
            self.delete_model(request, category)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin list for live and soft-deleted products."""

    list_display = (
        "sku",
        "name",
        "category",
        "selling_price",
        "status",
        "is_deleted",
        "updated_at",
    )
    search_fields = ("sku", "name", "description")
    list_filter = ("status", "unit", "category", "is_deleted")
    readonly_fields = (
        "id",
        "sku",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
        "is_deleted",
        "deleted_at",
    )

    def get_queryset(self, request: HttpRequest):
        """Include soft-deleted products for audit purposes."""
        return Product.all_objects.select_related(
            "category", "created_by", "updated_by"
        )

    def get_readonly_fields(self, request, obj=None):
        """Allow SKU only during Product creation."""
        fields = list(self.readonly_fields)
        if obj is None:
            fields.remove("sku")
        return fields

    def save_model(self, request, obj, form, change):
        """Populate audit users for admin writes."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def delete_model(self, request: HttpRequest, obj: Product) -> None:
        """Convert the Django Admin delete action into a soft delete."""
        ProductService.delete_product(
            obj.id,
            deleted_by=cast(User, request.user),
        )

    def delete_queryset(self, request: HttpRequest, queryset) -> None:
        """Soft-delete every selected live product."""
        for product in queryset.filter(is_deleted=False):
            ProductService.delete_product(
                product.id,
                deleted_by=cast(User, request.user),
            )
