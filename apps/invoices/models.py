from decimal import Decimal
from typing import ClassVar

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.customers.models import Customer
from apps.invoices.constants import InvoiceStatus
from apps.orders.models import Order
from shared.base_model import AuditModel


class Invoice(AuditModel):
    invoice_number = models.CharField(max_length=40, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="invoices")
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="invoice", null=True, blank=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    tax = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="VND")
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT)
    due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta(AuditModel.Meta):
        db_table = "invoices_invoice"
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=("customer", "status"), name="idx_invoice_customer_status"),
            models.Index(fields=("status",), name="idx_invoice_status"),
        )
        constraints: ClassVar[tuple[models.BaseConstraint, ...]] = (
            models.CheckConstraint(condition=Q(subtotal__gte=0), name="invoice_subtotal_nonnegative"),
            models.CheckConstraint(condition=Q(discount__gte=0), name="invoice_discount_nonnegative"),
            models.CheckConstraint(condition=Q(tax__gte=0), name="invoice_tax_nonnegative"),
            models.CheckConstraint(condition=Q(total_amount__gt=0), name="invoice_total_positive"),
        )

    def clean(self) -> None:
        if self.total_amount != self.subtotal - self.discount + self.tax:
            raise ValidationError("Invoice total does not match subtotal, discount and tax.")

    def __str__(self) -> str:
        return self.invoice_number