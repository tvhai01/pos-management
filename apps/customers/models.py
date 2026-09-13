"""
Models for the Customers app.

Defines:
- Customer: Core customer record. Foundation for Invoice, Order and
  Sales modules built in later sprints.
"""

from django.db import models
from django.utils import timezone

from apps.customers.constants import CustomerGender, CustomerStatus
from apps.customers.managers import CustomerManager
from apps.customers.validators import validate_phone_number
from shared.base_model import AuditModel


class Customer(AuditModel):
    """A customer of the POS Management System.

    Soft-deleted via `is_deleted` / `deleted_at` rather than a hard
    DELETE, so historical references from Invoice/Order/Payment
    (added in later sprints) never dangle.

    Attributes:
        customer_code: Unique business identifier (e.g., "CUS000123").
        full_name: The customer's display name.
        phone: Unique phone number, validated against PHONE_REGEX.
        email: Optional email address.
        gender: Optional gender (from CustomerGender TextChoices).
        birthday: Optional date of birth.
        address: Optional postal/delivery address.
        note: Optional free-text note.
        status: Lifecycle status (from CustomerStatus TextChoices).
        is_deleted: Soft-delete flag. False for all "live" customers.
        deleted_at: When the customer was soft-deleted (nullable).
    """

    customer_code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Customer Code",
    )
    full_name = models.CharField(
        max_length=150,
        verbose_name="Full Name",
    )
    phone = models.CharField(
        max_length=20,
        unique=True,
        validators=[validate_phone_number],
        verbose_name="Phone Number",
    )
    email = models.EmailField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Email Address",
    )
    gender = models.CharField(
        max_length=10,
        choices=CustomerGender.choices,
        blank=True,
        default="",
        verbose_name="Gender",
    )
    birthday = models.DateField(
        null=True,
        blank=True,
        verbose_name="Birthday",
    )
    address = models.TextField(
        blank=True,
        default="",
        verbose_name="Address",
    )
    note = models.TextField(
        blank=True,
        default="",
        verbose_name="Note",
    )
    status = models.CharField(
        max_length=20,
        choices=CustomerStatus.choices,
        default=CustomerStatus.ACTIVE,
        verbose_name="Status",
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Is Deleted",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Deleted At",
    )

    # Default manager excludes soft-deleted rows.
    objects = CustomerManager()
    # Unfiltered manager — includes soft-deleted rows (admin/audit only).
    all_objects = models.Manager()

    class Meta(AuditModel.Meta):
        db_table = "customers_customer"
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer_code"], name="idx_customer_code"),
            models.Index(fields=["phone"], name="idx_customer_phone"),
            models.Index(fields=["status"], name="idx_customer_status"),
            models.Index(fields=["is_deleted"], name="idx_customer_is_deleted"),
        ]

    def __str__(self) -> str:
        """Return a readable customer label."""
        return f"{self.customer_code} — {self.full_name}"

    def soft_delete(self) -> None:
        """Mark this customer as deleted without removing the row.

        Callers are responsible for saving the returned field changes
        (see CustomerService.delete_customer, which sets updated_by
        and persists in one .save() call).
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
