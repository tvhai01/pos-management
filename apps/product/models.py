"""Product catalogue models used by Inventory, Order, and Invoice modules."""

from decimal import Decimal
from typing import ClassVar

from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.product.constants import ProductStatus, ProductUnit
from apps.product.managers import ActiveRecordManager
from shared.base_model import AuditModel


class Category(AuditModel):
    """A soft-deletable category used to group products."""

    name = models.CharField(max_length=100, unique=True, verbose_name="Tên danh mục")
    description = models.TextField(blank=True, default="", verbose_name="Mô tả")
    is_deleted = models.BooleanField(default=False, verbose_name="Đã xóa")
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Thời điểm xóa",
    )

    objects = ActiveRecordManager()
    all_objects = models.Manager()

    class Meta(AuditModel.Meta):
        db_table = "product_category"
        verbose_name = "Danh mục"
        verbose_name_plural = "Danh mục"
        ordering = ["name"]  # noqa: RUF012 - Django Meta API expects a list
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=["is_deleted"], name="idx_category_is_deleted"),
        )

    def __str__(self) -> str:
        """Return the category name."""
        return self.name

    def soft_delete(self) -> None:
        """Mark the category as deleted without removing its row."""
        self.is_deleted = True
        self.deleted_at = timezone.now()


class Product(AuditModel):
    """A sellable product with an immutable, globally unique SKU."""

    sku = models.CharField(max_length=50, unique=True, verbose_name="Mã sản phẩm")
    name = models.CharField(max_length=255, verbose_name="Tên sản phẩm")
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Mô tả sản phẩm",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="Danh mục",
    )
    unit = models.CharField(
        max_length=50,
        choices=ProductUnit.choices,
        default=ProductUnit.PIECE,
        verbose_name="Đơn vị tính",
    )
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        verbose_name="Hình ảnh sản phẩm",
    )
    cost_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Giá nhập",
    )
    selling_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name="Giá bán",
    )
    status = models.CharField(
        max_length=10,
        choices=ProductStatus.choices,
        default=ProductStatus.ACTIVE,
        verbose_name="Trạng thái",
    )
    is_deleted = models.BooleanField(default=False, verbose_name="Đã xóa")
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Thời điểm xóa",
    )

    objects = ActiveRecordManager()
    all_objects = models.Manager()

    class Meta(AuditModel.Meta):
        db_table = "product_product"
        verbose_name = "Sản phẩm"
        verbose_name_plural = "Sản phẩm"
        ordering = ["-created_at"]  # noqa: RUF012 - Django Meta API expects a list
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=["status"], name="idx_product_status"),
            models.Index(fields=["is_deleted"], name="idx_product_is_deleted"),
        )
        constraints: ClassVar[tuple[models.BaseConstraint, ...]] = (
            models.CheckConstraint(
                condition=Q(cost_price__gte=Decimal("0.01")),
                name="product_cost_price_positive",
            ),
            models.CheckConstraint(
                condition=Q(selling_price__gt=F("cost_price")),
                name="product_selling_price_gt_cost",
            ),
        )

    def __str__(self) -> str:
        """Return a readable SKU and product name."""
        return f"{self.sku} - {self.name}"

    def soft_delete(self) -> None:
        """Mark the product as deleted without removing its row."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
