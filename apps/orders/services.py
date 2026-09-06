import logging
import uuid
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.invoices.constants import InvoiceStatus
from apps.orders.constants import OrderStatus
from apps.orders.models import Order, OrderItem
from apps.product.selectors import ProductSelector

logger = logging.getLogger(__name__)


class OrderService:
    @staticmethod
    @transaction.atomic
    def create_order(*, customer: Customer, items: list[dict[str, object]], discount: Decimal = Decimal("0"), tax: Decimal = Decimal("0"), currency: str = "VND", created_by: User | None = None) -> tuple[Order, object]:
        from apps.invoices.services import InvoiceService

        if not items:
            raise ValueError("At least one order item is required.")
        order_number = f"ORD-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"
        order = Order.objects.create(order_number=order_number, customer=customer, subtotal=Decimal("0"), discount=discount, tax=tax, total_amount=Decimal("0"), currency=currency.upper(), created_by=created_by, updated_by=created_by)
        subtotal = Decimal("0")
        for item in items:
            product = ProductSelector.get_sellable_product_for_update(item["product_id"])
            if product is None:
                raise ValueError("Product does not exist, is deleted, or is not active.")
            quantity = Decimal(str(item["quantity"]))
            if quantity <= 0:
                raise ValueError("Product quantity must be greater than zero.")
            item_subtotal = product.selling_price * quantity
            OrderItem.objects.create(order=order, product=product, product_name=product.name, product_sku=product.sku, unit_price=product.selling_price, quantity=quantity, subtotal=item_subtotal, total_amount=item_subtotal, created_by=created_by, updated_by=created_by)
            subtotal += item_subtotal
        total = subtotal - discount + tax
        if total <= 0:
            raise ValueError("Order total must be greater than zero.")
        order.subtotal = subtotal
        order.total_amount = total
        order.save(update_fields=["subtotal", "total_amount", "updated_at"])
        invoice = InvoiceService.create_invoice(order=order, customer=customer, invoice_number=f"INV-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}", subtotal=order.subtotal, discount=order.discount, tax=order.tax, currency=order.currency, created_by=created_by)
        logger.info("order.created order=%s invoice=%s", order.id, invoice.id)
        return order, invoice

    @staticmethod
    @transaction.atomic
    def transition(order_id: UUID | str, target: str, updated_by: User | None = None) -> Order:
        from apps.invoices.services import InvoiceService

        order = Order.objects.select_for_update().get(id=order_id)
        allowed = {OrderStatus.DRAFT: {OrderStatus.PENDING_PAYMENT, OrderStatus.CANCELLED}, OrderStatus.PENDING_PAYMENT: {OrderStatus.PAID, OrderStatus.CANCELLED}, OrderStatus.PAID: {OrderStatus.COMPLETED}, OrderStatus.CANCELLED: set(), OrderStatus.COMPLETED: set()}
        if target not in allowed[order.status]:
            raise ValueError(f"Invalid order transition: {order.status} -> {target}")
        order.status = target
        order.updated_by = updated_by
        now = timezone.now()
        if target == OrderStatus.PAID:
            order.paid_at = now
        elif target == OrderStatus.CANCELLED:
            order.cancelled_at = now
        elif target == OrderStatus.COMPLETED:
            order.completed_at = now
        order.save(update_fields=["status", "updated_by", "paid_at", "cancelled_at", "completed_at", "updated_at"])
        if target in (OrderStatus.PENDING_PAYMENT, OrderStatus.CANCELLED):
            invoice = order.invoice
            invoice_target = InvoiceStatus.PENDING_PAYMENT if target == OrderStatus.PENDING_PAYMENT else InvoiceStatus.CANCELLED
            if invoice.status != invoice_target:
                InvoiceService.transition(invoice.id, invoice_target, updated_by)
        return order