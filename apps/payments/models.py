from decimal import Decimal
from typing import ClassVar

from django.db import models
from django.db.models import Q

from apps.invoices.models import Invoice
from apps.payments.constants import PaymentMethod, PaymentStatus, Provider, TransactionType
from shared.base_model import AuditModel


class Payment(AuditModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    reference = models.CharField(max_length=64, unique=True)
    provider_reference = models.CharField(max_length=100, unique=True, null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="VND")
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    expires_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(AuditModel.Meta):
        db_table = "payments_payment"
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=("invoice",), name="idx_payment_invoice"),
            models.Index(fields=("status",), name="idx_payment_status"),
            models.Index(fields=("payment_method",), name="idx_payment_method"),
            models.Index(fields=("created_at",), name="idx_payment_created"),
        )
        constraints: ClassVar[tuple[models.BaseConstraint, ...]] = (
            models.CheckConstraint(condition=Q(amount__gt=0), name="payment_amount_positive"),
        )

    def __str__(self) -> str:
        return self.reference


class PaymentTransaction(AuditModel):
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="transactions")
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="transactions")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_transaction_id = models.CharField(max_length=150, null=True, blank=True)
    provider_reference = models.CharField(max_length=100, null=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="VND")
    status = models.CharField(max_length=20, choices=PaymentStatus.choices)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    transaction_content = models.TextField(blank=True, default="")
    raw_response = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta(AuditModel.Meta):
        db_table = "payments_transaction"
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=("payment",), name="idx_transaction_payment"),
            models.Index(fields=("invoice",), name="idx_transaction_invoice"),
            models.Index(fields=("provider",), name="idx_transaction_provider"),
            models.Index(fields=("status",), name="idx_transaction_status"),
            models.Index(fields=("created_at",), name="idx_transaction_created"),
        )
        constraints: ClassVar[tuple[models.BaseConstraint, ...]] = (
            models.UniqueConstraint(fields=("provider", "provider_transaction_id"), name="uniq_provider_transaction"),
        )


class PaymentAudit(AuditModel):
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="audit_entries")
    changed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="payment_audit_entries")
    field_name = models.CharField(max_length=80)
    old_value = models.TextField(blank=True, default="")
    new_value = models.TextField(blank=True, default="")
    reason = models.TextField()

    class Meta(AuditModel.Meta):
        db_table = "payments_audit"
        indexes: ClassVar[tuple[models.Index, ...]] = (
            models.Index(fields=("payment", "created_at"), name="idx_payment_audit_created"),
        )