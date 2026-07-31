"""
Constants for the Customers app.

Defines closed enumerations for customer status and gender using
Django's TextChoices for type safety and DB-level validation.
"""

from django.db import models


class CustomerStatus(models.TextChoices):
    """Valid lifecycle states for a customer record."""

    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    BLOCKED = "blocked", "Blocked"


class CustomerGender(models.TextChoices):
    """Valid gender options for a customer record."""

    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"


# =============================================================================
# Customer Messages
# =============================================================================

MSG_CUSTOMER_CREATED: str = "Customer created successfully."
MSG_CUSTOMER_UPDATED: str = "Customer updated successfully."
MSG_CUSTOMER_DELETED: str = "Customer deleted successfully."
MSG_CUSTOMER_NOT_FOUND: str = "Customer not found."
MSG_CUSTOMER_CODE_EXISTS: str = "A customer with this code already exists."
MSG_CUSTOMER_PHONE_EXISTS: str = "A customer with this phone number already exists."
MSG_INVALID_PHONE_FORMAT: str = (
    "Phone number must be 9-15 digits, optionally starting with '+'."
)

# =============================================================================
# Search / Ordering Configuration
# =============================================================================

CUSTOMER_SEARCH_FIELDS: tuple[str, ...] = (
    "customer_code",
    "full_name",
    "phone",
    "email",
)
CUSTOMER_ORDERING_FIELDS: tuple[str, ...] = (
    "customer_code",
    "full_name",
    "status",
    "created_at",
    "updated_at",
)
