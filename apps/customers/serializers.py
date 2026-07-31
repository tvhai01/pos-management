"""
Serializers for the Customers app.

Provides input validation and output formatting for customer CRUD,
search, and listing endpoints.

Validation belongs here — never in views.
"""

from typing import Any
from uuid import UUID

from rest_framework import serializers

from apps.customers.constants import CustomerGender, CustomerStatus
from apps.customers.models import Customer
from apps.customers.selectors import CustomerSelector
from apps.customers.validators import is_valid_phone_number

# =============================================================================
# Output Serializers
# =============================================================================


class CustomerListSerializer(serializers.ModelSerializer):
    """Serializes Customer data for list views (lightweight)."""

    class Meta:
        model = Customer
        fields: tuple[str, ...] = (
            "id",
            "customer_code",
            "full_name",
            "phone",
            "email",
            "status",
            "created_at",
        )


class CustomerDetailSerializer(serializers.ModelSerializer):
    """Serializes full Customer data for detail/create/update responses."""

    created_by = serializers.SerializerMethodField()
    updated_by = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields: tuple[str, ...] = (
            "id",
            "customer_code",
            "full_name",
            "phone",
            "email",
            "gender",
            "birthday",
            "address",
            "note",
            "status",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )

    def get_created_by(self, obj: Customer) -> str | None:
        """Return the email of the user who created this customer."""
        return obj.created_by.email if obj.created_by_id else None

    def get_updated_by(self, obj: Customer) -> str | None:
        """Return the email of the user who last updated this customer."""
        return obj.updated_by.email if obj.updated_by_id else None


# =============================================================================
# Input Serializers
# =============================================================================


class CreateCustomerSerializer(serializers.Serializer):
    """Validates input for creating a new customer.

    Fields:
        customer_code: Required unique business code.
        full_name: Required display name.
        phone: Required unique phone number (format-validated).
        email: Optional email address.
        gender: Optional gender.
        birthday: Optional date of birth.
        address: Optional address.
        note: Optional free-text note.
        status: Optional lifecycle status (defaults to ACTIVE).
    """

    customer_code = serializers.CharField(max_length=20, required=True)
    full_name = serializers.CharField(max_length=150, required=True)
    phone = serializers.CharField(max_length=20, required=True)
    email = serializers.EmailField(
        max_length=255, required=False, default="", allow_blank=True
    )
    gender = serializers.ChoiceField(
        choices=CustomerGender.choices, required=False, default=""
    )
    birthday = serializers.DateField(required=False, allow_null=True, default=None)
    address = serializers.CharField(required=False, default="", allow_blank=True)
    note = serializers.CharField(required=False, default="", allow_blank=True)
    status = serializers.ChoiceField(
        choices=CustomerStatus.choices,
        required=False,
        default=CustomerStatus.ACTIVE,
    )

    def validate_customer_code(self, value: str) -> str:
        """Validate that the customer code is unique.

        Args:
            value: The customer code.

        Returns:
            The validated customer code.

        Raises:
            serializers.ValidationError: If the code is already in use.
        """
        if CustomerSelector.code_exists(value):
            raise serializers.ValidationError(
                f"A customer with the code '{value}' already exists."
            )
        return value

    def validate_phone(self, value: str) -> str:
        """Validate phone format and uniqueness.

        Args:
            value: The phone number.

        Returns:
            The validated phone number.

        Raises:
            serializers.ValidationError: If the format is invalid or
                the phone number is already in use.
        """
        if not is_valid_phone_number(value):
            raise serializers.ValidationError(
                "Phone number must be 9-15 digits, optionally starting with '+'."
            )
        if CustomerSelector.phone_exists(value):
            raise serializers.ValidationError(
                f"A customer with the phone number '{value}' already exists."
            )
        return value


class UpdateCustomerSerializer(serializers.Serializer):
    """Validates input for updating an existing customer.

    All fields are optional. Uniqueness checks exclude the customer
    being updated (see `context["customer_id"]`).
    """

    customer_code = serializers.CharField(max_length=20, required=False)
    full_name = serializers.CharField(max_length=150, required=False)
    phone = serializers.CharField(max_length=20, required=False)
    email = serializers.EmailField(max_length=255, required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=CustomerGender.choices, required=False)
    birthday = serializers.DateField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=CustomerStatus.choices, required=False)

    def validate_customer_code(self, value: str) -> str:
        """Validate that the customer code is unique (excluding self).

        Args:
            value: The customer code.

        Returns:
            The validated customer code.

        Raises:
            serializers.ValidationError: If another customer uses this code.
        """
        customer_id: UUID | None = self.context.get("customer_id")
        if CustomerSelector.code_exists(value, exclude_id=customer_id):
            raise serializers.ValidationError(
                f"A customer with the code '{value}' already exists."
            )
        return value

    def validate_phone(self, value: str) -> str:
        """Validate phone format and uniqueness (excluding self).

        Args:
            value: The phone number.

        Returns:
            The validated phone number.

        Raises:
            serializers.ValidationError: If the format is invalid or
                another customer already uses this phone number.
        """
        if not is_valid_phone_number(value):
            raise serializers.ValidationError(
                "Phone number must be 9-15 digits, optionally starting with '+'."
            )
        customer_id: UUID | None = self.context.get("customer_id")
        if CustomerSelector.phone_exists(value, exclude_id=customer_id):
            raise serializers.ValidationError(
                f"A customer with the phone number '{value}' already exists."
            )
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Ensure at least one field is provided for the update.

        Args:
            attrs: The validated field data.

        Returns:
            The validated data.

        Raises:
            serializers.ValidationError: If no fields were provided.
        """
        if not attrs:
            raise serializers.ValidationError(
                "At least one field must be provided to update the customer."
            )
        return attrs
