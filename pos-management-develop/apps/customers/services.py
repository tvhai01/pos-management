"""
Service layer for the Customers app.

Contains business logic for customer creation, update, and (soft)
deletion. Services are called from views and never from models
directly.
"""

import logging
from datetime import date
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.customers.constants import CustomerStatus
from apps.customers.exceptions import CustomerNotFoundError
from apps.customers.models import Customer
from apps.customers.selectors import CustomerSelector

logger = logging.getLogger(__name__)

_UPDATABLE_FIELDS: set[str] = {
    "customer_code",
    "full_name",
    "phone",
    "email",
    "gender",
    "birthday",
    "address",
    "note",
    "status",
}


class CustomerService:
    """Business logic for customer management."""

    @staticmethod
    @transaction.atomic
    def create_customer(
        customer_code: str,
        full_name: str,
        phone: str,
        email: str = "",
        gender: str = "",
        birthday: date | None = None,
        address: str = "",
        note: str = "",
        status: str = CustomerStatus.ACTIVE,
        created_by: User | None = None,
    ) -> Customer:
        """Create a new customer.

        Uniqueness of customer_code/phone is already enforced by the
        serializer; the DB unique constraint is the final backstop.

        Args:
            customer_code: Unique business code.
            full_name: Customer display name.
            phone: Unique phone number.
            email: Optional email address.
            gender: Optional gender.
            birthday: Optional date of birth.
            address: Optional address.
            note: Optional free-text note.
            status: Lifecycle status (defaults to ACTIVE).
            created_by: The User performing the creation (nullable).

        Returns:
            The created Customer instance.
        """
        customer = Customer.objects.create(
            customer_code=customer_code,
            full_name=full_name,
            phone=phone,
            email=email,
            gender=gender,
            birthday=birthday,
            address=address,
            note=note,
            status=status,
            created_by=created_by,
            updated_by=created_by,
        )

        logger.info("Customer created: %s (%s)", customer.customer_code, full_name)
        return customer

    @staticmethod
    @transaction.atomic
    def update_customer(
        customer_id: UUID,
        updated_by: User | None = None,
        **kwargs: Any,
    ) -> Customer:
        """Update an existing customer.

        Only fields explicitly provided (and non-None) are updated.

        Args:
            customer_id: The customer's UUID.
            updated_by: The User performing the update (nullable).
            **kwargs: Fields to update.

        Returns:
            The updated Customer instance.

        Raises:
            CustomerNotFoundError: If the customer doesn't exist.
        """
        customer = CustomerSelector.get_customer_by_id(customer_id)
        if customer is None:
            raise CustomerNotFoundError()

        update_fields: list[str] = []
        for field, value in kwargs.items():
            if field in _UPDATABLE_FIELDS and value is not None:
                setattr(customer, field, value)
                update_fields.append(field)

        if update_fields:
            customer.updated_by = updated_by
            update_fields.extend(["updated_by", "updated_at"])
            customer.save(update_fields=update_fields)
            logger.info(
                "Customer updated: %s (fields=%s)",
                customer.customer_code,
                update_fields,
            )

        return customer

    @staticmethod
    @transaction.atomic
    def delete_customer(customer_id: UUID, deleted_by: User | None = None) -> None:
        """Soft-delete a customer.

        The row is never physically removed — `is_deleted` is set and
        `deleted_at` is stamped, so historical references (invoices,
        orders) from later sprints remain intact.

        Args:
            customer_id: The customer's UUID.
            deleted_by: The User performing the deletion (nullable).

        Raises:
            CustomerNotFoundError: If the customer doesn't exist.
        """
        customer = CustomerSelector.get_customer_by_id(customer_id)
        if customer is None:
            raise CustomerNotFoundError()

        customer.is_deleted = True
        customer.deleted_at = timezone.now()
        customer.updated_by = deleted_by
        customer.save(
            update_fields=["is_deleted", "deleted_at", "updated_by", "updated_at"]
        )

        logger.info("Customer soft-deleted: %s", customer.customer_code)
