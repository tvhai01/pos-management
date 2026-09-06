from django.db import models


class InvoiceStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PENDING_PAYMENT = "PENDING_PAYMENT", "Pending payment"
    PAID = "PAID", "Paid"
    CANCELLED = "CANCELLED", "Cancelled"


INVOICE_SEARCH_FIELDS = ("invoice_number", "customer__full_name", "customer__phone")
INVOICE_ORDERING_FIELDS = ("invoice_number", "total_amount", "status", "created_at")