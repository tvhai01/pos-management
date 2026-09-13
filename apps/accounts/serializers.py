"""
Serializers for the Accounts app.

Provides input validation and output formatting for authentication,
user profile, and RBAC endpoints.

Validation belongs here — never in views.
"""

from typing import Any
from uuid import UUID

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import serializers

from apps.accounts.models import Permission, Role, User


# =============================================================================
# Authentication Serializers
# =============================================================================


class LoginSerializer(serializers.Serializer):
    """Validates login credentials.

    Fields:
        email: Required email address.
        password: Required password (write-only).
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
    )


class LogoutSerializer(serializers.Serializer):
    """Validates the refresh token for logout.

    Fields:
        refresh: The refresh token to blacklist.
    """

    refresh = serializers.CharField(required=True)


class RefreshTokenSerializer(serializers.Serializer):
    """Validates the refresh token for token rotation.

    Fields:
        refresh: The current refresh token.
    """

    refresh = serializers.CharField(required=True)


class ChangePasswordSerializer(serializers.Serializer):
    """Validates password change input.

    Fields:
        old_password: The current password.
        new_password: The new password (validated against Django validators).
        confirm_password: Must match new_password.
    """

    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
    )
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
    )

    def validate_new_password(self, value: str) -> str:
        """Validate the new password against Django's password validators.

        Args:
            value: The new password string.

        Returns:
            The validated password string.

        Raises:
            serializers.ValidationError: If the password fails validation.
        """
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages) from e
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate that new_password and confirm_password match.

        Args:
            attrs: The validated field data.

        Returns:
            The validated data.

        Raises:
            serializers.ValidationError: If passwords don't match.
        """
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "New password and confirm password do not match."}
            )
        return attrs


# =============================================================================
# User Serializers
# =============================================================================


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializes user profile data for the /auth/me/ endpoint.

    Read-only fields: id, email, roles, date_joined.
    Writable fields: full_name, phone.
    """

    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields: tuple[str, ...] = (
            "id",
            "email",
            "full_name",
            "phone",
            "is_active",
            "roles",
            "date_joined",
            "created_at",
            "updated_at",
        )
        read_only_fields: tuple[str, ...] = (
            "id",
            "email",
            "is_active",
            "roles",
            "date_joined",
            "created_at",
            "updated_at",
        )

    def get_roles(self, obj: User) -> list[str]:
        """Return the user's active role names.

        Args:
            obj: The User instance.

        Returns:
            List of active role name strings.
        """
        return obj.role_names


class UpdateProfileSerializer(serializers.Serializer):
    """Validates profile update input.

    Only full_name and phone can be updated.
    """

    full_name = serializers.CharField(max_length=150, required=False)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)


# =============================================================================
# Permission Serializers
# =============================================================================


class PermissionSerializer(serializers.ModelSerializer):
    """Serializes Permission data."""

    class Meta:
        model = Permission
        fields: tuple[str, ...] = (
            "id",
            "name",
            "action",
            "resource",
            "description",
        )
        read_only_fields: tuple[str, ...] = ("id",)


# =============================================================================
# Role Serializers
# =============================================================================


class RoleListSerializer(serializers.ModelSerializer):
    """Serializes Role data for list views (lightweight)."""

    permission_count = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields: tuple[str, ...] = (
            "id",
            "name",
            "description",
            "is_active",
            "permission_count",
            "user_count",
            "created_at",
        )

    def get_permission_count(self, obj: Role) -> int:
        """Return the number of permissions assigned to this role."""
        return obj.permissions.count()

    def get_user_count(self, obj: Role) -> int:
        """Return the number of users assigned to this role."""
        return obj.users.count()


class RoleDetailSerializer(serializers.ModelSerializer):
    """Serializes Role data with full permission details."""

    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Role
        fields: tuple[str, ...] = (
            "id",
            "name",
            "description",
            "is_active",
            "permissions",
            "created_at",
            "updated_at",
        )


class CreateRoleSerializer(serializers.Serializer):
    """Validates input for creating a new role.

    Fields:
        name: Required unique role name.
        description: Optional description.
        permission_ids: Optional list of Permission UUIDs to assign.
    """

    name = serializers.CharField(max_length=50, required=True)
    description = serializers.CharField(required=False, default="")
    permission_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )

    def validate_name(self, value: str) -> str:
        """Validate that the role name is unique.

        Args:
            value: The role name.

        Returns:
            The validated role name.

        Raises:
            serializers.ValidationError: If a role with this name exists.
        """
        if Role.objects.filter(name=value).exists():
            raise serializers.ValidationError(
                f"A role with the name '{value}' already exists."
            )
        return value

    def validate_permission_ids(self, value: list[UUID]) -> list[UUID]:
        """Validate that all permission IDs exist.

        Args:
            value: List of Permission UUIDs.

        Returns:
            The validated list of UUIDs.

        Raises:
            serializers.ValidationError: If any permission ID is invalid.
        """
        if value:
            existing_count = Permission.objects.filter(id__in=value).count()
            if existing_count != len(value):
                raise serializers.ValidationError(
                    "One or more permission IDs are invalid."
                )
        return value


class UpdateRoleSerializer(serializers.Serializer):
    """Validates input for updating an existing role.

    All fields are optional for partial updates.
    """

    name = serializers.CharField(max_length=50, required=False)
    description = serializers.CharField(required=False)
    is_active = serializers.BooleanField(required=False)
    permission_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
    )

    def validate_name(self, value: str) -> str:
        """Validate that the role name is unique (excluding current role).

        Args:
            value: The role name.

        Returns:
            The validated role name.

        Raises:
            serializers.ValidationError: If another role with this name exists.
        """
        role_id = self.context.get("role_id")
        if Role.objects.filter(name=value).exclude(id=role_id).exists():
            raise serializers.ValidationError(
                f"A role with the name '{value}' already exists."
            )
        return value

    def validate_permission_ids(self, value: list[UUID]) -> list[UUID]:
        """Validate that all permission IDs exist.

        Args:
            value: List of Permission UUIDs.

        Returns:
            The validated list of UUIDs.

        Raises:
            serializers.ValidationError: If any permission ID is invalid.
        """
        if value:
            existing_count = Permission.objects.filter(id__in=value).count()
            if existing_count != len(value):
                raise serializers.ValidationError(
                    "One or more permission IDs are invalid."
                )
        return value


# =============================================================================
# Staff (User Management) Serializers
# =============================================================================


class UserListSerializer(serializers.ModelSerializer):
    """Serializes User data for the staff list view (lightweight)."""

    role_names = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields: tuple[str, ...] = (
            "id",
            "email",
            "full_name",
            "phone",
            "is_active",
            "role_names",
            "date_joined",
        )

    def get_role_names(self, obj: User) -> list[str]:
        """Return the user's active role names."""
        return obj.role_names


class UserDetailSerializer(serializers.ModelSerializer):
    """Serializes User data with full role details for the staff detail view."""

    roles = RoleListSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields: tuple[str, ...] = (
            "id",
            "email",
            "full_name",
            "phone",
            "is_active",
            "roles",
            "date_joined",
            "created_at",
            "updated_at",
        )


class CreateUserSerializer(serializers.Serializer):
    """Validates input for creating a new staff user.

    Fields:
        email: Required unique email address.
        full_name: Required display name.
        password: Required initial password (validated against Django validators).
        phone: Optional phone number.
        role_ids: Optional list of Role UUIDs to assign.
    """

    email = serializers.EmailField(required=True)
    full_name = serializers.CharField(max_length=150, required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
    )
    phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True, default=""
    )
    role_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )

    def validate_email(self, value: str) -> str:
        """Validate that the email is not already in use.

        Args:
            value: The email address.

        Returns:
            The validated email address.

        Raises:
            serializers.ValidationError: If a user with this email exists.
        """
        from apps.accounts.selectors import UserSelector

        if UserSelector.email_exists(value):
            raise serializers.ValidationError(
                f"A user with the email '{value}' already exists."
            )
        return value

    def validate_password(self, value: str) -> str:
        """Validate the password against Django's password validators.

        Args:
            value: The password string.

        Returns:
            The validated password string.

        Raises:
            serializers.ValidationError: If the password fails validation.
        """
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages) from e
        return value

    def validate_role_ids(self, value: list[UUID]) -> list[UUID]:
        """Validate that all role IDs exist.

        Args:
            value: List of Role UUIDs.

        Returns:
            The validated list of UUIDs.

        Raises:
            serializers.ValidationError: If any role ID is invalid.
        """
        if value:
            existing_count = Role.objects.filter(id__in=value).count()
            if existing_count != len(value):
                raise serializers.ValidationError("One or more role IDs are invalid.")
        return value


class UpdateUserSerializer(serializers.Serializer):
    """Validates input for updating an existing staff user.

    All fields are optional for partial updates. Email cannot be changed.
    """

    full_name = serializers.CharField(max_length=150, required=False)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    role_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
    )

    def validate_role_ids(self, value: list[UUID]) -> list[UUID]:
        """Validate that all role IDs exist.

        Args:
            value: List of Role UUIDs.

        Returns:
            The validated list of UUIDs.

        Raises:
            serializers.ValidationError: If any role ID is invalid.
        """
        if value:
            existing_count = Role.objects.filter(id__in=value).count()
            if existing_count != len(value):
                raise serializers.ValidationError("One or more role IDs are invalid.")
        return value
