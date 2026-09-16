from decimal import Decimal

import pytest
from django.test import override_settings

from apps.customers.models import Customer
from apps.invoices.constants import InvoiceStatus
from apps.invoices.services import InvoiceService
from apps.orders.services import OrderService
from apps.payments.constants import PaymentStatus
from apps.payments.models import Payment, PaymentTransaction
from apps.payments.paypal import PayPalService
from apps.payments.services import PaymentService
from apps.payments.sepay import SePayService
from apps.product.constants import ProductStatus, ProductUnit
from apps.product.models import Category
from apps.product.services import ProductService


@pytest.fixture
def pending_invoice(create_user):
    customer = Customer.objects.create(
        customer_code="CUS-PAY-002",
        full_name="Webhook Customer",
        phone="0900000002",
        created_by=create_user,
        updated_by=create_user,
    )
    invoice = InvoiceService.create_invoice(
        customer=customer,
        invoice_number="INV-PAY-002",
        subtotal=Decimal("500000"),
        created_by=create_user,
    )
    return InvoiceService.transition(invoice.id, InvoiceStatus.PENDING_PAYMENT, create_user)


@pytest.mark.django_db
@override_settings(SEPAY_WEBHOOK_SECRET="test-webhook-secret", SEPAY_KEY="test-api-key")
def test_qr_payment_and_duplicate_webhook(pending_invoice, create_user, monkeypatch):
    monkeypatch.setattr(
        SePayService,
        "create_checkout",
        lambda *args, **kwargs: {"checkout_url": "", "qr_url": "", "qr_code": ""},
    )
    payment, _ = PaymentService.create_qr_payment(pending_invoice.id, created_by=create_user)
    payload = {"order_invoice_number": payment.reference, "transaction_id": "tx-001", "amount": "500000", "currency": "VND", "status": PaymentStatus.SUCCESS}
    signature = SePayService.signature(payload)
    PaymentService.process_webhook(payload, signature)
    PaymentService.process_webhook(payload, signature)
    payment.refresh_from_db()
    assert payment.status == PaymentStatus.SUCCESS
    assert PaymentTransaction.objects.filter(provider_transaction_id="tx-001").count() == 1
    assert pending_invoice.__class__.objects.get(id=pending_invoice.id).status == InvoiceStatus.PAID


@pytest.mark.django_db
@override_settings(
    SEPAY_WEBHOOK_SECRET="test-webhook-secret",
    SEPAY_BANK_ACCOUNT_XID="SBSEPAYXPIMWGG2CHT7",
)
def test_bankhub_webhook_matches_invoice_content(pending_invoice, create_user):
    payment, _ = PaymentService.create_qr_payment(
        pending_invoice.id, created_by=create_user
    )
    payload = {
        "bank_account_xid": "SBSEPAYXPIMWGG2CHT7",
        "transfer_type": "credit",
        "amount_in": "500000",
        "transaction_content": pending_invoice.invoice_number,
        "transaction_id": "bankhub-tx-001",
        "currency": "VND",
        "status": PaymentStatus.SUCCESS,
    }
    signature = SePayService.signature(payload)

    transaction = PaymentService.process_webhook(payload, signature)

    payment.refresh_from_db()
    pending_invoice.refresh_from_db()
    assert transaction.transaction_content == pending_invoice.invoice_number
    assert payment.status == PaymentStatus.SUCCESS
    assert pending_invoice.status == InvoiceStatus.PAID


@pytest.mark.django_db
def test_qr_payment_promotes_draft_invoice_to_pending(create_user, monkeypatch):
    customer = Customer.objects.create(
        customer_code="CUS-PAY-003",
        full_name="Draft Invoice Customer",
        phone="0900000003",
        created_by=create_user,
        updated_by=create_user,
    )
    category = Category.objects.create(name="Payment Category", created_by=create_user, updated_by=create_user)
    product = ProductService.create_product(
        sku="SKU-PAY-003",
        name="Draft Invoice Product",
        cost_price=Decimal("10000"),
        selling_price=Decimal("50000"),
        category_id=category.id,
        unit=ProductUnit.PIECE,
        status=ProductStatus.ACTIVE,
        created_by=create_user,
    )
    _, invoice = OrderService.create_order(
        customer=customer,
        items=[{"product_id": product.id, "quantity": 2}],
        created_by=create_user,
    )
    assert invoice.status == InvoiceStatus.DRAFT
    monkeypatch.setattr(
        SePayService,
        "create_checkout",
        lambda *args, **kwargs: {"checkout_url": "", "qr_url": "", "qr_code": ""},
    )

    payment, checkout = PaymentService.create_qr_payment(invoice.id, created_by=create_user)

    invoice.refresh_from_db()
    assert invoice.status == InvoiceStatus.PENDING_PAYMENT
    assert payment.status == PaymentStatus.PENDING
    assert checkout["qr_url"].startswith("https://api.qrserver.com")


@pytest.mark.django_db
def test_paypal_payment_creates_checkout_and_marks_pending(create_user, monkeypatch):
    customer = Customer.objects.create(
        customer_code="CUS-PAY-004",
        full_name="PayPal Customer",
        phone="0900000004",
        created_by=create_user,
        updated_by=create_user,
    )
    category = Category.objects.create(name="Paypal Category", created_by=create_user, updated_by=create_user)
    product = ProductService.create_product(
        sku="SKU-PAY-004",
        name="PayPal Product",
        cost_price=Decimal("10000"),
        selling_price=Decimal("50000"),
        category_id=category.id,
        unit=ProductUnit.PIECE,
        status=ProductStatus.ACTIVE,
        created_by=create_user,
    )
    _, invoice = OrderService.create_order(
        customer=customer,
        items=[{"product_id": product.id, "quantity": 2}],
        created_by=create_user,
    )
    monkeypatch.setattr(
        PayPalService,
        "create_checkout",
        lambda *args, **kwargs: {
            "checkout_url": "https://www.sandbox.paypal.com/checkoutnow?token=TESTPAYPAL",
            "qr_url": "",
            "qr_code": "TESTPAYPAL",
            "deeplink_url": "",
            "provider": "PAYPAL",
        },
    )

    payment, checkout = PaymentService.create_paypal_payment(invoice.id, created_by=create_user)

    invoice.refresh_from_db()
    assert invoice.status == InvoiceStatus.PENDING_PAYMENT
    assert payment.status == PaymentStatus.PENDING
    assert checkout["provider"] == "PAYPAL"
    assert checkout["checkout_url"].startswith("https://")


@pytest.mark.django_db
def test_manual_payment_promotes_draft_invoice_to_pending(create_user):
    customer = Customer.objects.create(
        customer_code="CUS-PAY-005",
        full_name="Manual Draft Customer",
        phone="0900000005",
        created_by=create_user,
        updated_by=create_user,
    )
    category = Category.objects.create(name="Manual Category", created_by=create_user, updated_by=create_user)
    product = ProductService.create_product(
        sku="SKU-PAY-005",
        name="Manual Draft Product",
        cost_price=Decimal("10000"),
        selling_price=Decimal("50000"),
        category_id=category.id,
        unit=ProductUnit.PIECE,
        status=ProductStatus.ACTIVE,
        created_by=create_user,
    )
    _, invoice = OrderService.create_order(
        customer=customer,
        items=[{"product_id": product.id, "quantity": 2}],
        created_by=create_user,
    )

    payment = PaymentService.create_manual_payment(
        invoice.id,
        amount=invoice.total_amount,
        note="Cash receipt",
        created_by=create_user,
    )

    invoice.refresh_from_db()
    assert invoice.status == InvoiceStatus.PAID
    assert payment.status == PaymentStatus.SUCCESS


@pytest.mark.django_db
def test_manual_payment_marks_invoice_paid(pending_invoice, create_user):
    payment = PaymentService.create_manual_payment(
        pending_invoice.id,
        amount=Decimal("500000"),
        note="Cash receipt",
        created_by=create_user,
    )
    assert payment.status == PaymentStatus.SUCCESS
    assert pending_invoice.__class__.objects.get(id=pending_invoice.id).status == InvoiceStatus.PAID


@pytest.mark.django_db
def test_success_payment_cannot_be_cancelled(pending_invoice, create_user):
    payment = PaymentService.create_manual_payment(
        pending_invoice.id,
        amount=Decimal("500000"),
        created_by=create_user,
    )
    with pytest.raises(ValueError):
        PaymentService.cancel_payment(payment.id, cancelled_by=create_user)