"""
Selector layer for the Accounts app.

Contains read-only query logic for user, role, and permission data retrieval.
Selectors are called from services and never directly from views.
"""

import logging
from uuid import UUID

from django.db.models import QuerySet

from apps.accounts.models import Permission, Role, User

logger = logging.getLogger(__name__)


class UserSelector:
    """Read-only queries for User data."""

    @staticmethod
    def get_user_by_id(user_id: UUID) -> User | None:
        """Retrieve a user by their UUID.

        Args:
            user_id: The user's UUID primary key.

        Returns:
            The User instance, or None if not found.
        """
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_user_by_email(email: str) -> User | None:
        """Retrieve a user by their email address.

        Args:
            email: The user's email address.

        Returns:
            The User instance, or None if not found.
        """
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_active_users() -> QuerySet[User]:
        """Return a queryset of all active users.

        Returns:
            QuerySet of active User instances.
        """
        return User.objects.filter(is_active=True)

    @staticmethod
    def get_user_with_roles(user_id: UUID) -> User | None:
        """Retrieve a user with prefetched roles and permissions.

        Optimizes queries by prefetching the roles and their permissions
        in a single database round-trip.

        Args:
            user_id: The user's UUID primary key.

        Returns:
            The User instance with prefetched roles, or None if not found.
        """
        try:
            return User.objects.prefetch_related(
                "roles__permissions",
            ).get(id=user_id)
        except User.DoesNotExist:
            return None


class PermissionSelector:
    """Read-only queries for RBAC permission checking."""

    @staticmethod
    def user_has_permission(
        user: User,
        action: str,
        resource: str,
    ) -> bool:
        """Check if a user has a specific permission via their roles.

        Superusers always return True (bypass RBAC).
        For regular users, checks if any of their active roles
        contain the specified action-resource permission.

        Args:
            user: The User instance to check.
            action: The permission action (e.g., "create").
            resource: The permission resource (e.g., "user").

        Returns:
            True if the user has the permission, False otherwise.
        """
        # Superusers bypass all RBAC checks
        if user.is_superuser:
            return True

        has_perm = user.roles.filter(
            is_active=True,
            permissions__action=action,
            permissions__resource=resource,
        ).exists()

        if not has_perm:
            logger.debug(
                "Permission denied: user=%s action=%s resource=%s",
                user.email,
                action,
                resource,
            )

        return has_perm

    @staticmethod
    def get_user_permissions(user: User) -> QuerySet[Permission]:
        """Get all permissions for a user across all active roles.

        Args:
            user: The User instance.

        Returns:
            QuerySet of Permission instances (distinct).
        """
        return Permission.objects.filter(
            roles__users=user,
            roles__is_active=True,
        ).distinct()


class RoleSelector:
    """Read-only queries for Role data."""

    @staticmethod
    def get_all_roles() -> QuerySet[Role]:
        """Return all roles with prefetched permissions.

        Returns:
            QuerySet of Role instances.
        """
        return Role.objects.prefetch_related("permissions").all()

    @staticmethod
    def get_active_roles() -> QuerySet[Role]:
        """Return all active roles.

        Returns:
            QuerySet of active Role instances.
        """
        return Role.objects.filter(is_active=True).prefetch_related("permissions")

    @staticmethod
    def get_role_by_id(role_id: UUID) -> Role | None:
        """Retrieve a role by its UUID with prefetched permissions.

        Args:
            role_id: The role's UUID primary key.

        Returns:
            The Role instance, or None if not found.
        """
        try:
            return Role.objects.prefetch_related("permissions").get(id=role_id)
        except Role.DoesNotExist:
            return None

    @staticmethod
    def get_all_permissions() -> QuerySet[Permission]:
        """Return all permissions ordered by resource and action.

        Returns:
            QuerySet of Permission instances.
        """
        return Permission.objects.all()

    @staticmethod
    def role_has_users(role: Role) -> bool:
        """Check if a role has any assigned users.

        Args:
            role: The Role instance to check.

        Returns:
            True if the role has assigned users, False otherwise.
        """
        return role.users.exists()
