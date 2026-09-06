from decimal import Decimal

import pytest

from apps.customers.models import Customer
from apps.invoices.constants import InvoiceStatus
from apps.orders.constants import OrderStatus
from apps.orders.models import OrderItem
from apps.orders.services import OrderService
from apps.payments.constants import PaymentStatus
from apps.payments.services import PaymentService
from apps.product.constants import ProductStatus, ProductUnit
from apps.product.models import Category, Product
from apps.product.services import ProductService


@pytest.mark.django_db
def test_existing_product_flows_to_order_invoice_and_payment(create_user):
    customer = Customer.objects.create(customer_code="CUS-ORDER-001", full_name="Order Customer", phone="0900000011", created_by=create_user, updated_by=create_user)
    category = Category.objects.create(name="Order Category", created_by=create_user, updated_by=create_user)
    product = ProductService.create_product(sku="SKU-ORDER-001", name="Existing Product", cost_price=Decimal("50"), selling_price=Decimal("100"), category_id=category.id, unit=ProductUnit.PIECE, status=ProductStatus.ACTIVE, created_by=create_user)
    order, invoice = OrderService.create_order(customer=customer, items=[{"product_id": product.id, "quantity": 2}], created_by=create_user)
    item = OrderItem.objects.get(order=order)
    assert item.product_id == product.id
    assert item.product_name == "Existing Product"
    assert item.unit_price == Decimal("100")
    assert order.total_amount == Decimal("200")
    assert invoice.order_id == order.id
    assert invoice.total_amount == order.total_amount

    ProductService.update_product(product.id, updated_by=create_user, selling_price=Decimal("120"))
    item.refresh_from_db()
    assert item.unit_price == Decimal("100")

    OrderService.transition(order.id, OrderStatus.PENDING_PAYMENT, create_user)
    assert invoice.__class__.objects.get(id=invoice.id).status == InvoiceStatus.PENDING_PAYMENT
    payment = PaymentService.create_manual_payment(invoice.id, amount=Decimal("200"), created_by=create_user)
    order.refresh_from_db()
    invoice.refresh_from_db()
    assert payment.status == PaymentStatus.SUCCESS
    assert invoice.status == InvoiceStatus.PAID
    assert order.status == OrderStatus.PAID