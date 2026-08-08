import uuid
from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated",
    )
    deleted_at = models.DateTimeField("Thời gian xóa", null=True, blank=True, db_index=True)

    class Meta:
        abstract = True


class Category(BaseModel):
    name = models.CharField("Tên danh mục", max_length=255)
    description = models.TextField("Mô tả", blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Danh mục"
        verbose_name_plural = "Danh mục"

    def __str__(self):
        return self.name


class Product(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Đang kinh doanh"
        INACTIVE = "inactive", "Ngừng kinh doanh"

    class Unit(models.TextChoices):
        CAI = "cái", "Cái"
        CHIEC = "chiếc", "Chiếc"
        HOP = "hộp", "Hộp"
        GOI = "gói", "Gói"
        KG = "kg", "Kg"
        GRAM = "gram", "Gram"
        LIT = "lít", "Lít"
        ML = "ml", "Ml"
        MET = "mét", "Mét"
        CAN = "can", "Can"
        CHAI = "chai", "Chai"
        LOC = "lốc", "Lốc"
        THUNG = "thùng", "Thùng"
        BAO = "bao", "Bao"

    sku = models.CharField("Mã sản phẩm / SKU", max_length=50, unique=True)
    name = models.CharField("Tên sản phẩm", max_length=255)
    description = models.TextField("Mô tả", blank=True, null=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="Danh mục"
    )
    unit = models.CharField(
        "Đơn vị tính",
        max_length=50,
        choices=Unit.choices,
        blank=True,
        default=Unit.CAI
    )
    image = models.ImageField("Hình ảnh", upload_to="products/", null=True, blank=True)
    cost_price = models.DecimalField(
        "Giá nhập", max_digits=14, decimal_places=2, default=0
    )
    selling_price = models.DecimalField(
        "Giá bán", max_digits=14, decimal_places=2, default=0
    )
    status = models.CharField(
        "Trạng thái",
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Sản phẩm"
        verbose_name_plural = "Danh sách sản phẩm"

    def __str__(self):
        return f"{self.sku} - {self.name}"

    # -------------------------------------------------------------------------
    # PRODUCT_TXN_GUARD — tìm keyword này khi thêm module Kho / Order / Invoice
    #
    # Hiện chưa có app Order/Stock/Invoice → hasattr(...) = False → không lỗi.
    # Sau này thêm FK từ model con → Product, BẮT BUỘC dùng đúng related_name:
    #
    #   StockMovement.product  → related_name="stock_movements"
    #   OrderItem.product      → related_name="order_items"
    #   InvoiceLine.product    → related_name="invoices"   (hoặc model tương đương)
    #
    # Khuyến nghị: on_delete=models.PROTECT trên các FK trên.
    #
    # Các chỗ gọi method này (cùng keyword PRODUCT_TXN_GUARD):
    #   - apps/product/admin.py      (_hard_delete_products, ProductTrashAdmin)
    #   - apps/product/views.py      (product_hard_delete_view, product_soft_delete_view)
    #   - apps/dashboard/forms.py    (ProductUIForm — khóa SKU)
    #   - apps/product/forms.py      (ProductUIForm — khóa SKU)
    #   - templates/.../trash.html   (ẩn nút "Xóa hẳn")
    # -------------------------------------------------------------------------
    def has_transaction_history(self) -> bool:
        """True nếu SP đã phát sinh giao dịch (kho, đơn hàng, hóa đơn). Xem PRODUCT_TXN_GUARD."""
        has_stock = hasattr(self, "stock_movements") and self.stock_movements.exists()
        has_orders = hasattr(self, "order_items") and self.order_items.exists()
        has_invoices = hasattr(self, "invoices") and self.invoices.exists()
        return has_stock or has_orders or has_invoices

#thùng rác
class CategoryTrash(Category):
    class Meta:
        proxy = True
        verbose_name = "Thùng rác danh mục"
        verbose_name_plural = "Thùng rác danh mục"


class ProductTrash(Product):
    class Meta:
        proxy = True
        verbose_name = "Thùng rác sản phẩm"
        verbose_name_plural = "Thùng rác sản phẩm"