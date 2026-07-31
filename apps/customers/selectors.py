"""
Selector layer for the Customers app.

Contains read-only query logic for customer data retrieval.
Selectors are called from services and views, and never build
business logic — only queries.
"""

import logging
from uuid import UUID

from django.db.models import Q, QuerySet

from apps.customers.models import Customer

logger = logging.getLogger(__name__)


class CustomerSelector:
    """Read-only queries for Customer data."""

    @staticmethod
    def get_customer_by_id(customer_id: UUID | str) -> Customer | None:
        """Retrieve a non-deleted customer by their UUID.

        Args:
            customer_id: The customer's UUID primary key.

        Returns:
            The Customer instance, or None if not found (or deleted).
        """
        try:
            return Customer.objects.get(id=customer_id)
        except (Customer.DoesNotExist, ValueError, TypeError):
            return None

    @staticmethod
    def get_customer_by_code(customer_code: str) -> Customer | None:
        """Retrieve a non-deleted customer by their unique code.

        Args:
            customer_code: The customer's unique business code.

        Returns:
            The Customer instance, or None if not found (or deleted).
        """
        try:
            return Customer.objects.get(customer_code=customer_code)
        except Customer.DoesNotExist:
            return None

    @staticmethod
    def get_all_customers() -> QuerySet[Customer]:
        """Return the base queryset of all non-deleted customers.

        Filtering, searching, ordering, and pagination are applied by
        the view via DRF filter backends configured project-wide.

        Returns:
            QuerySet of non-deleted Customer instances.
        """
        return Customer.objects.all()

    @staticmethod
    def search_customers(search: str = "", status: str = "") -> QuerySet[Customer]:
        """Return non-deleted customers matching a search term and/or status.

        Used by server-rendered views (`apps.dashboard`) which have no DRF
        filter backends available. The DRF API list endpoint keeps using
        `get_all_customers()` + `DjangoFilterBackend`/`SearchFilter` instead —
        this method is the plain-queryset equivalent for non-DRF callers.

        Args:
            search: Substring to match against customer_code, full_name,
                phone, or email. Empty string disables the search filter.
            status: Exact CustomerStatus value to filter by. Empty string
                disables the status filter.

        Returns:
            QuerySet of matching, non-deleted Customer instances.
        """
        queryset = Customer.objects.all()
        if search:
            queryset = queryset.filter(
                Q(customer_code__icontains=search)
                | Q(full_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(email__icontains=search)
            )
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    @staticmethod
    def code_exists(customer_code: str, exclude_id: UUID | str | None = None) -> bool:
        """Check whether a customer_code is already in use.

        Checks against ALL rows (including soft-deleted) because the
        `customer_code` column carries a table-wide unique constraint.

        Args:
            customer_code: The code to check.
            exclude_id: A customer ID to exclude (for update checks).

        Returns:
            True if the code is already in use, False otherwise.
        """
        queryset = Customer.all_objects.filter(customer_code=customer_code)
        if exclude_id is not None:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()

    @staticmethod
    def phone_exists(phone: str, exclude_id: UUID | str | None = None) -> bool:
        """Check whether a phone number is already in use.

        Checks against ALL rows (including soft-deleted) because the
        `phone` column carries a table-wide unique constraint.

        Args:
            phone: The phone number to check.
            exclude_id: A customer ID to exclude (for update checks).

        Returns:
            True if the phone number is already in use, False otherwise.
        """
        queryset = Customer.all_objects.filter(phone=phone)
        if exclude_id is not None:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()
