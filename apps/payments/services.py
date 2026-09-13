import logging
import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.invoices.constants import InvoiceStatus
from apps.invoices.models import Invoice
from apps.invoices.services import InvoiceService
from apps.payments.constants import PaymentMethod, PaymentStatus, Provider, TransactionType
from apps.payments.models import Payment, PaymentAudit, PaymentTransaction
from apps.payments.sepay import SePayService

logger = logging.getLogger(__name__)


class PaymentService:
    @staticmethod
    @transaction.atomic
    def create_qr_payment(invoice_id, *, created_by=None, return_url: str = "") -> tuple[Payment, dict[str, object]]:
        invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        if invoice.status != InvoiceStatus.PENDING_PAYMENT:
            raise ValueError("Invoice must be pending payment.")
        if invoice.total_amount <= 0:
            raise ValueError("Invoice total must be greater than zero.")
        reference = f"PAY-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"
        payment = Payment.objects.create(invoice=invoice, reference=reference, provider_reference=reference, amount=invoice.total_amount, currency=invoice.currency, payment_method=PaymentMethod.QR, expires_at=timezone.now() + timedelta(minutes=15), created_by=created_by, updated_by=created_by)
        PaymentTransaction.objects.create(payment=payment, invoice=invoice, provider=Provider.SEPAY, provider_reference=reference, transaction_type=TransactionType.PAYMENT, amount=payment.amount, currency=payment.currency, status=PaymentStatus.PENDING, payment_method=payment.payment_method, transaction_content=reference, processed_at=timezone.now(), created_by=created_by, updated_by=created_by)
        checkout = SePayService.create_checkout(reference, payment.amount, payment.currency, return_url)
        logger.info("payment.created payment=%s invoice=%s", payment.id, invoice.id)
        return payment, checkout

    @staticmethod
    @transaction.atomic
    def create_manual_payment(invoice_id, *, amount: Decimal, payment_date=None, reference: str = "", note: str = "", payer_information: str = "", created_by=None) -> Payment:
        invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        if invoice.status != InvoiceStatus.PENDING_PAYMENT:
            raise ValueError("Invoice must be pending payment.")
        if amount != invoice.total_amount:
            raise ValueError("Manual payment amount must equal the invoice total.")
        payment = Payment.objects.create(invoice=invoice, reference=reference or f"MAN-{uuid.uuid4().hex[:12].upper()}", amount=amount, currency=invoice.currency, payment_method=PaymentMethod.MANUAL, status=PaymentStatus.SUCCESS, processed_at=payment_date or timezone.now(), metadata={"note": note, "payer_information": payer_information}, created_by=created_by, updated_by=created_by)
        PaymentTransaction.objects.create(payment=payment, invoice=invoice, provider=Provider.MANUAL, provider_reference=payment.reference, transaction_type=TransactionType.PAYMENT, amount=amount, currency=invoice.currency, status=PaymentStatus.SUCCESS, payment_method=PaymentMethod.MANUAL, transaction_content=note, processed_at=payment.processed_at, created_by=created_by, updated_by=created_by)
        if amount >= invoice.total_amount:
            InvoiceService.transition(invoice.id, InvoiceStatus.PAID, created_by)
        logger.info("payment.success payment=%s method=MANUAL", payment.id)
        return payment

    @staticmethod
    @transaction.atomic
    def process_webhook(payload: dict[str, object], supplied_signature: str | None) -> PaymentTransaction:
        if not SePayService.verify_webhook(payload, supplied_signature):
            logger.warning("sepay.webhook.rejected")
            raise ValueError("Invalid webhook signature.")
        reference = str(payload.get("order_invoice_number") or payload.get("reference") or "")
        transaction_id = str(payload.get("transaction_id") or payload.get("id") or "")
        if not transaction_id:
            raise ValueError("Provider transaction ID is required.")
        payment = Payment.objects.select_for_update().filter(reference=reference).first() or Payment.objects.select_for_update().filter(provider_reference=reference).first()
        if payment is None:
            raise ValueError("Payment not found.")
        amount = Decimal(str(payload.get("amount", "0")))
        currency = str(payload.get("currency") or payment.currency).upper()
        if amount != payment.amount or currency != payment.currency:
            raise ValueError("Payment amount or currency mismatch.")
        target_status = str(payload.get("status", PaymentStatus.SUCCESS)).upper()
        if target_status not in PaymentStatus.values:
            raise ValueError("Invalid payment status.")
        existing = PaymentTransaction.objects.filter(provider=Provider.SEPAY, provider_transaction_id=transaction_id).first() if transaction_id else None
        if existing:
            logger.info("sepay.transaction.duplicate transaction=%s", transaction_id)
            return existing
        now = timezone.now()
        ledger = PaymentTransaction.objects.create(payment=payment, invoice=payment.invoice, provider=Provider.SEPAY, provider_transaction_id=transaction_id or None, provider_reference=reference, transaction_type=TransactionType.PAYMENT, amount=amount, currency=currency, status=target_status, payment_method=payment.payment_method, transaction_content=str(payload.get("content", "")), raw_response=payload, processed_at=now, created_by=payment.created_by, updated_by=payment.updated_by)
        allowed = {PaymentStatus.PENDING: {PaymentStatus.PROCESSING, PaymentStatus.SUCCESS, PaymentStatus.FAILED, PaymentStatus.EXPIRED, PaymentStatus.CANCELLED}, PaymentStatus.PROCESSING: {PaymentStatus.SUCCESS, PaymentStatus.FAILED, PaymentStatus.EXPIRED, PaymentStatus.CANCELLED}, PaymentStatus.SUCCESS: set(), PaymentStatus.FAILED: set(), PaymentStatus.EXPIRED: set(), PaymentStatus.CANCELLED: set()}
        if target_status not in allowed[payment.status] and target_status != payment.status:
            raise ValueError(f"Invalid payment transition: {payment.status} -> {target_status}")
        if payment.status != target_status:
            payment.status = target_status
            payment.processed_at = now if target_status in (PaymentStatus.SUCCESS, PaymentStatus.FAILED, PaymentStatus.EXPIRED, PaymentStatus.CANCELLED) else None
            payment.save(update_fields=["status", "processed_at", "updated_at"])
        if target_status == PaymentStatus.SUCCESS and amount >= payment.invoice.total_amount and payment.invoice.status == InvoiceStatus.PENDING_PAYMENT:
            InvoiceService.transition(payment.invoice_id, InvoiceStatus.PAID, payment.updated_by)
        logger.info("sepay.transaction.created transaction=%s status=%s", ledger.id, target_status)
        return ledger

    @staticmethod
    @transaction.atomic
    def cancel_payment(payment_id, *, cancelled_by=None) -> Payment:
        payment = Payment.objects.select_for_update().get(id=payment_id)
        if payment.status not in (PaymentStatus.PENDING, PaymentStatus.PROCESSING):
            raise ValueError("Only pending or processing payments can be cancelled.")
        payment.status = PaymentStatus.CANCELLED
        payment.processed_at = timezone.now()
        payment.updated_by = cancelled_by
        payment.save(update_fields=["status", "processed_at", "updated_by", "updated_at"])
        if payment.provider_reference:
            SePayService.cancel_order(payment.provider_reference)
        logger.info("payment.cancelled payment=%s", payment.id)
        return payment

    @staticmethod
    @transaction.atomic
    def expire_payment(payment_id) -> Payment:
        payment = Payment.objects.select_for_update().get(id=payment_id)
        if payment.status == PaymentStatus.PENDING and payment.expires_at and timezone.now() > payment.expires_at:
            payment.status = PaymentStatus.EXPIRED
            payment.processed_at = timezone.now()
            payment.save(update_fields=["status", "processed_at", "updated_at"])
        return payment

    @staticmethod
    @transaction.atomic
    def edit_manual_payment(payment_id, *, amount: Decimal, reason: str, changed_by=None) -> Payment:
        payment = Payment.objects.select_for_update().get(id=payment_id)
        if payment.payment_method != PaymentMethod.MANUAL:
            raise ValueError("Only manual payments can be edited.")
        old_amount = payment.amount
        payment.amount = amount
        payment.updated_by = changed_by
        payment.save(update_fields=["amount", "updated_by", "updated_at"])
        PaymentAudit.objects.create(payment=payment, changed_by=changed_by, field_name="amount", old_value=str(old_amount), new_value=str(amount), reason=reason, created_by=changed_by, updated_by=changed_by)
        return payment