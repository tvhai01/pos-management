from decimal import Decimal

import pytest
from django.test import override_settings

from apps.customers.models import Customer
from apps.invoices.constants import InvoiceStatus
from apps.invoices.services import InvoiceService
from apps.payments.constants import PaymentStatus
from apps.payments.models import Payment, PaymentTransaction
from apps.payments.services import PaymentService
from apps.payments.sepay import SePayService


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
@override_settings(SEPAY_SECRET_KEY="test-secret", SEPAY_MERCHANT_ID="sandbox-merchant")
def test_qr_payment_and_duplicate_webhook(pending_invoice, create_user):
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