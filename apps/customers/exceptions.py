"""
Custom exceptions for the Customers app.

App-specific exceptions that inherit from shared.exceptions.ApplicationError.
Each exception maps to a specific HTTP status code and error message.
"""

from rest_framework import status

from apps.customers.constants import MSG_CUSTOMER_NOT_FOUND
from shared.exceptions import ApplicationError


class CustomerNotFoundError(ApplicationError):
    """Raised when a customer cannot be found (or is soft-deleted)."""

    status_code: int = status.HTTP_404_NOT_FOUND
    default_detail: str = MSG_CUSTOMER_NOT_FOUND
    default_code: str = "customer_not_found"
