from decimal import Decimal
from typing import ClassVar

from django.db import models
from django.db.models import Q

from apps.customers.models import Customer
from apps.orders.constants import OrderStatus
from apps.product.models import Product
from shared.base_model import AuditModel


class Order(AuditModel):
    order_number = models.CharField(max_length=40, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    tax = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="VND")
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.DRAFT)
    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta(AuditModel.Meta):
        db_table = "orders_order"
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=("customer", "status"), name="idx_order_customer_status"),
            models.Index(fields=("status",), name="idx_order_status"),
        )
        constraints: ClassVar[tuple[models.BaseConstraint, ...]] = (
            models.CheckConstraint(condition=Q(total_amount__gt=0), name="order_total_positive"),
            models.CheckConstraint(condition=Q(subtotal__gte=0), name="order_subtotal_nonnegative"),
        )

    def __str__(self) -> str:
        return self.order_number


class OrderItem(AuditModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=50)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    tax = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta(AuditModel.Meta):
        db_table = "orders_order_item"
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=("order",), name="idx_order_item_order"),
            models.Index(fields=("product",), name="idx_order_item_product"),
        )
        constraints: ClassVar[tuple[models.BaseConstraint, ...]] = (
            models.CheckConstraint(condition=Q(quantity__gt=0), name="order_item_quantity_positive"),
            models.CheckConstraint(condition=Q(unit_price__gte=0), name="order_item_price_nonnegative"),
        )