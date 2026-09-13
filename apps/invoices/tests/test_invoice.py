from decimal import Decimal

import pytest

from apps.customers.models import Customer
from apps.invoices.constants import InvoiceStatus
from apps.invoices.models import Invoice
from apps.invoices.services import InvoiceService


@pytest.fixture
def invoice(create_user):
    customer = Customer.objects.create(
        customer_code="CUS-PAY-001",
        full_name="Payment Customer",
        phone="0900000001",
        created_by=create_user,
        updated_by=create_user,
    )
    return InvoiceService.create_invoice(
        customer=customer,
        invoice_number="INV-PAY-001",
        subtotal=Decimal("100000"),
        created_by=create_user,
    )


@pytest.mark.django_db
def test_invoice_transitions(invoice, create_user):
    InvoiceService.transition(invoice.id, InvoiceStatus.PENDING_PAYMENT, create_user)
    InvoiceService.transition(invoice.id, InvoiceStatus.CANCELLED, create_user)
    assert Invoice.objects.get(id=invoice.id).status == InvoiceStatus.CANCELLED


@pytest.mark.django_db
def test_paid_invoice_cannot_transition(invoice, create_user):
    InvoiceService.transition(invoice.id, InvoiceStatus.PENDING_PAYMENT, create_user)
    InvoiceService.transition(invoice.id, InvoiceStatus.PAID, create_user)
    with pytest.raises(ValueError):
        InvoiceService.transition(invoice.id, InvoiceStatus.CANCELLED, create_user)