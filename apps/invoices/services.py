import logging
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.invoices.constants import InvoiceStatus
from apps.invoices.models import Invoice
from apps.orders.constants import OrderStatus
from apps.orders.models import Order

logger = logging.getLogger(__name__)


class InvoiceService:
    @staticmethod
    @transaction.atomic
    def create_invoice(*, customer, invoice_number: str, subtotal: Decimal, discount: Decimal = Decimal("0"), tax: Decimal = Decimal("0"), currency: str = "VND", due_at=None, order=None, created_by: User | None = None) -> Invoice:
        total = subtotal - discount + tax
        return Invoice.objects.create(
            invoice_number=invoice_number,
            customer=customer,
            order=order,
            subtotal=subtotal,
            discount=discount,
            tax=tax,
            total_amount=total,
            currency=currency.upper(),
            due_at=due_at,
            created_by=created_by,
            updated_by=created_by,
        )

    @staticmethod
    @transaction.atomic
    def transition(invoice_id: UUID | str, target: str, updated_by: User | None = None) -> Invoice:
        invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        allowed = {
            InvoiceStatus.DRAFT: {InvoiceStatus.PENDING_PAYMENT, InvoiceStatus.CANCELLED},
            InvoiceStatus.PENDING_PAYMENT: {InvoiceStatus.PAID, InvoiceStatus.CANCELLED},
            InvoiceStatus.PAID: set(),
            InvoiceStatus.CANCELLED: set(),
        }
        if target not in allowed[invoice.status]:
            raise ValueError(f"Invalid invoice transition: {invoice.status} -> {target}")
        invoice.status = target
        invoice.updated_by = updated_by
        if target == InvoiceStatus.PAID:
            invoice.paid_at = timezone.now()
            if invoice.order_id:
                order = Order.objects.select_for_update().get(id=invoice.order_id)
                if order.status == OrderStatus.PENDING_PAYMENT:
                    order.status = OrderStatus.PAID
                    order.paid_at = invoice.paid_at
                    order.save(update_fields=["status", "paid_at", "updated_at"])
        if target == InvoiceStatus.CANCELLED:
            invoice.cancelled_at = timezone.now()
        invoice.save(update_fields=["status", "updated_by", "paid_at", "cancelled_at", "updated_at"])
        return invoice