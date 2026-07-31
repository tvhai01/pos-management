"""
Permission classes for the Accounts app.

Custom DRF permission classes for RBAC enforcement.
All permission checking is delegated to PermissionSelector.
"""

import logging
from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.selectors import PermissionSelector

logger = logging.getLogger(__name__)


class IsSuperAdmin(BasePermission):
    """Allow access only to superusers.

    Use this for endpoints that should only be accessible
    by the highest-level administrators.
    """

    message: str = "Only super administrators can perform this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if the request user is a superuser.

        Args:
            request: The incoming DRF request.
            view: The view being accessed.

        Returns:
            True if the user is a superuser, False otherwise.
        """
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )


class HasPermission(BasePermission):
    """Reusable RBAC permission class.

    Checks if the authenticated user has a specific action-resource
    permission via their assigned roles.

    Usage in views:
        class MyView(APIView):
            permission_classes = [IsAuthenticated, HasPermission]
            required_permission = {"action": "create", "resource": "user"}

    Or with the factory method:
        permission_classes = [IsAuthenticated, HasPermission.with_permission("create", "user")]
    """

    message: str = "You do not have permission to perform this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if the user has the required permission.

        The required permission is read from the view's
        `required_permission` attribute, which must be a dict
        with 'action' and 'resource' keys.

        Args:
            request: The incoming DRF request.
            view: The view being accessed.

        Returns:
            True if the user has the required permission.
        """
        if not request.user or not request.user.is_authenticated:
            return False

        # Get required permission from the view
        required_permission: dict[str, str] | None = getattr(
            view, "required_permission", None
        )

        if required_permission is None:
            logger.warning(
                "View %s uses HasPermission but has no required_permission attribute.",
                view.__class__.__name__,
            )
            return False

        action = required_permission.get("action", "")
        resource = required_permission.get("resource", "")

        return PermissionSelector.user_has_permission(
            user=request.user,
            action=action,
            resource=resource,
        )

    @classmethod
    def with_permission(cls, action: str, resource: str) -> type["HasPermission"]:
        """Factory method to create a permission class with specific requirements.

        Creates a new permission class with the action and resource
        baked in, avoiding the need for a `required_permission` attribute
        on the view.

        Args:
            action: The required permission action.
            resource: The required permission resource.

        Returns:
            A new permission class configured for the specified permission.

        Usage:
            permission_classes = [
                IsAuthenticated,
                HasPermission.with_permission("create", "user"),
            ]
        """

        class _HasSpecificPermission(cls):  # type: ignore[misc]
            """Dynamically created permission class."""

            def has_permission(self, request: Request, view: APIView) -> bool:
                if not request.user or not request.user.is_authenticated:
                    return False
                return PermissionSelector.user_has_permission(
                    user=request.user,
                    action=action,
                    resource=resource,
                )

        _HasSpecificPermission.__name__ = (
            f"HasPermission_{action}_{resource}"
        )
        _HasSpecificPermission.__qualname__ = (
            f"HasPermission.with_permission.{action}_{resource}"
        )
        return _HasSpecificPermission
