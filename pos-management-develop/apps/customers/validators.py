"""
Field-level validators for the Customers app.

Shared between the model layer (DB-level enforcement via RegexValidator)
and the serializer layer (early, user-friendly validation errors).
"""

import re

from django.core.validators import RegexValidator

from apps.customers.constants import MSG_INVALID_PHONE_FORMAT

# Accepts 9-15 digits, with an optional leading '+'.
PHONE_REGEX: str = r"^\+?[0-9]{9,15}$"

validate_phone_number = RegexValidator(
    regex=PHONE_REGEX,
    message=MSG_INVALID_PHONE_FORMAT,
)


def is_valid_phone_number(value: str) -> bool:
    """Check whether a phone number matches the required format.

    Args:
        value: The phone number string to validate.

    Returns:
        True if the phone number matches PHONE_REGEX, False otherwise.
    """
    return bool(re.match(PHONE_REGEX, value))
