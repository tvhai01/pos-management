from django.db import models


class OrderStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PENDING_PAYMENT = "PENDING_PAYMENT", "Pending payment"
    PAID = "PAID", "Paid"
    CANCELLED = "CANCELLED", "Cancelled"
    COMPLETED = "COMPLETED", "Completed"


ORDER_SEARCH_FIELDS = ("order_number", "customer__full_name", "customer__phone")
ORDER_ORDERING_FIELDS = ("order_number", "total_amount", "status", "created_at")