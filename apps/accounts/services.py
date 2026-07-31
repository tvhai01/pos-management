"""
Service layer for the Accounts app.

Contains business logic for authentication, user management, and RBAC.
Services are called from views and never from models directly.
"""

import logging
from typing import Any
from uuid import UUID

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from rest_framework_simplejwt.exceptions import TokenError as JWTTokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.exceptions import (
    InactiveAccountError,
    InvalidCredentialsError,
    OldPasswordIncorrectError,
    PasswordMismatchError,
    RoleHasUsersError,
    RoleNotFoundError,
    TokenError,
)
from apps.accounts.models import Permission, Role, User, UserRole
from apps.accounts.selectors import RoleSelector

logger = logging.getLogger(__name__)


class AuthService:
    """Business logic for authentication operations.

    Handles login, logout, token refresh, and password management.
    """

    @staticmethod
    def login(email: str, password: str) -> dict[str, Any]:
        """Authenticate a user and return JWT tokens.

        Args:
            email: The user's email address.
            password: The user's password.

        Returns:
            A dict containing access token, refresh token, and user data.

        Raises:
            InvalidCredentialsError: If email/password combination is wrong.
            InactiveAccountError: If the user's account is deactivated.
        """
        user = authenticate(email=email, password=password)

        if user is None:
            logger.warning("Failed login attempt for email: %s", email)
            raise InvalidCredentialsError()

        if not user.is_active:
            logger.warning("Login attempt by inactive user: %s", email)
            raise InactiveAccountError()

        refresh = RefreshToken.for_user(user)

        logger.info("Successful login: %s", email)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "roles": user.role_names,
            },
        }

    @staticmethod
    def logout(refresh_token: str) -> None:
        """Blacklist a refresh token (logout).

        Args:
            refresh_token: The refresh token string to blacklist.

        Raises:
            TokenError: If the token is invalid or already blacklisted.
        """
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info("Token blacklisted successfully.")
        except JWTTokenError as e:
            logger.warning("Logout failed — invalid token: %s", str(e))
            raise TokenError() from e

    @staticmethod
    def refresh_token(refresh_token: str) -> dict[str, str]:
        """Refresh an access token using a valid refresh token.

        Args:
            refresh_token: The current refresh token string.

        Returns:
            A dict with new access and refresh tokens.

        Raises:
            TokenError: If the refresh token is invalid or expired.
        """
        try:
            token = RefreshToken(refresh_token)
            return {
                "access": str(token.access_token),
                "refresh": str(token),
            }
        except JWTTokenError as e:
            logger.warning("Token refresh failed: %s", str(e))
            raise TokenError() from e

    @staticmethod
    def change_password(
        user: User,
        old_password: str,
        new_password: str,
        confirm_password: str,
    ) -> None:
        """Change a user's password.

        Validates old password, checks new/confirm match,
        and runs Django's password validators.

        Args:
            user: The User instance changing their password.
            old_password: The current password.
            new_password: The new password.
            confirm_password: Confirmation of the new password.

        Raises:
            OldPasswordIncorrectError: If old_password doesn't match.
            PasswordMismatchError: If new_password != confirm_password.
            ApplicationError: If new password fails Django validators.
        """
        if not user.check_password(old_password):
            raise OldPasswordIncorrectError()

        if new_password != confirm_password:
            raise PasswordMismatchError()

        # Run Django's built-in password validators
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as e:
            from shared.exceptions import ApplicationError

            raise ApplicationError(detail=e.messages) from e

        user.set_password(new_password)
        user.save(update_fields=["password"])

        logger.info("Password changed for user: %s", user.email)


class UserService:
    """Business logic for user profile management."""

    @staticmethod
    def update_profile(
        user: User,
        **kwargs: Any,
    ) -> User:
        """Update a user's profile fields.

        Only updates fields that are explicitly provided.
        Email cannot be changed through this method.

        Args:
            user: The User instance to update.
            **kwargs: Fields to update (full_name, phone).

        Returns:
            The updated User instance.
        """
        allowed_fields: set[str] = {"full_name", "phone"}
        update_fields: list[str] = []

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(user, field, value)
                update_fields.append(field)

        if update_fields:
            update_fields.append("updated_at")
            user.save(update_fields=update_fields)
            logger.info(
                "Profile updated for user %s: fields=%s",
                user.email,
                update_fields,
            )

        return user


class RoleService:
    """Business logic for RBAC role management."""

    @staticmethod
    @transaction.atomic
    def create_role(
        name: str,
        description: str = "",
        permission_ids: list[UUID] | None = None,
    ) -> Role:
        """Create a new role with optional permissions.

        Args:
            name: The role name (must be unique).
            description: Optional description.
            permission_ids: List of Permission UUIDs to assign.

        Returns:
            The created Role instance.
        """
        role = Role.objects.create(
            name=name,
            description=description,
        )

        if permission_ids:
            permissions = Permission.objects.filter(id__in=permission_ids)
            role.permissions.set(permissions)

        logger.info("Role created: %s", name)
        return role

    @staticmethod
    @transaction.atomic
    def update_role(
        role_id: UUID,
        **kwargs: Any,
    ) -> Role:
        """Update an existing role.

        Args:
            role_id: The role's UUID.
            **kwargs: Fields to update (name, description, is_active, permission_ids).

        Returns:
            The updated Role instance.

        Raises:
            RoleNotFoundError: If the role doesn't exist.
        """
        role = RoleSelector.get_role_by_id(role_id)
        if role is None:
            raise RoleNotFoundError()

        allowed_fields: set[str] = {"name", "description", "is_active"}
        update_fields: list[str] = []

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(role, field, value)
                update_fields.append(field)

        if update_fields:
            update_fields.append("updated_at")
            role.save(update_fields=update_fields)

        # Handle permission assignment separately
        permission_ids = kwargs.get("permission_ids")
        if permission_ids is not None:
            permissions = Permission.objects.filter(id__in=permission_ids)
            role.permissions.set(permissions)

        logger.info("Role updated: %s (fields=%s)", role.name, update_fields)
        return role

    @staticmethod
    @transaction.atomic
    def delete_role(role_id: UUID) -> None:
        """Delete a role if it has no assigned users.

        Args:
            role_id: The role's UUID.

        Raises:
            RoleNotFoundError: If the role doesn't exist.
            RoleHasUsersError: If the role has assigned users.
        """
        role = RoleSelector.get_role_by_id(role_id)
        if role is None:
            raise RoleNotFoundError()

        if RoleSelector.role_has_users(role):
            raise RoleHasUsersError()

        role_name = role.name
        role.delete()
        logger.info("Role deleted: %s", role_name)

    @staticmethod
    @transaction.atomic
    def assign_role_to_user(
        user: User,
        role_id: UUID,
        assigned_by: User | None = None,
    ) -> UserRole:
        """Assign a role to a user.

        Args:
            user: The User to receive the role.
            role_id: The UUID of the Role to assign.
            assigned_by: The User performing the assignment (nullable).

        Returns:
            The created UserRole instance.

        Raises:
            RoleNotFoundError: If the role doesn't exist.
        """
        role = RoleSelector.get_role_by_id(role_id)
        if role is None:
            raise RoleNotFoundError()

        user_role, created = UserRole.objects.get_or_create(
            user=user,
            role=role,
            defaults={"assigned_by": assigned_by},
        )

        if created:
            logger.info(
                "Role '%s' assigned to user '%s' by '%s'",
                role.name,
                user.email,
                assigned_by.email if assigned_by else "system",
            )

        return user_role

    @staticmethod
    @transaction.atomic
    def remove_role_from_user(user: User, role_id: UUID) -> None:
        """Remove a role from a user.

        Args:
            user: The User to remove the role from.
            role_id: The UUID of the Role to remove.

        Raises:
            RoleNotFoundError: If the role doesn't exist.
        """
        role = RoleSelector.get_role_by_id(role_id)
        if role is None:
            raise RoleNotFoundError()

        deleted_count, _ = UserRole.objects.filter(
            user=user,
            role=role,
        ).delete()

        if deleted_count > 0:
            logger.info(
                "Role '%s' removed from user '%s'",
                role.name,
                user.email,
            )
