from django.db import models


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"
    EXPIRED = "EXPIRED", "Expired"
    CANCELLED = "CANCELLED", "Cancelled"


class PaymentMethod(models.TextChoices):
    QR = "QR", "QR"
    SEPAY = "SEPAY", "SePay"
    MANUAL = "MANUAL", "Manual"
    PAYPAL = "PAYPAL", "PayPal"


class Provider(models.TextChoices):
    SEPAY = "SEPAY", "SePay"
    MOMO = "MOMO", "MoMo"
    PAYPAL = "PAYPAL", "PayPal"
    MANUAL = "MANUAL", "Manual"


class TransactionType(models.TextChoices):
    PAYMENT = "PAYMENT", "Payment"
    CAPTURE = "CAPTURE", "Capture"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"


PAYMENT_SEARCH_FIELDS = ("reference", "invoice__invoice_number", "provider_reference")
PAYMENT_ORDERING_FIELDS = ("created_at", "amount", "status", "expires_at")