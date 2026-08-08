"""
Views for the Accounts app.

Contains:
- Health check endpoint (Sprint 0)
- Authentication endpoints (Sprint 1)
- User profile endpoints (Sprint 1)
- RBAC management endpoints (Sprint 1)

Views are thin — all business logic lives in services.
"""

import logging
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import connection

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.constants import (
    MSG_LOGIN_SUCCESS,
    MSG_LOGOUT_SUCCESS,
    MSG_PASSWORD_CHANGED,
    MSG_PROFILE_UPDATED,
    MSG_REFRESH_SUCCESS,
    MSG_ROLE_CREATED,
    MSG_ROLE_DELETED,
    MSG_ROLE_UPDATED,
)
from apps.accounts.permissions import HasPermission
from apps.accounts.selectors import RoleSelector
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    CreateRoleSerializer,
    LoginSerializer,
    LogoutSerializer,
    PermissionSerializer,
    RefreshTokenSerializer,
    RoleDetailSerializer,
    RoleListSerializer,
    UpdateProfileSerializer,
    UpdateRoleSerializer,
    UserProfileSerializer,
)
from apps.accounts.services import AuthService, RoleService, UserService
from shared.response import error_response, success_response

logger = logging.getLogger(__name__)


# =============================================================================
# Health Check (Sprint 0)
# =============================================================================


class HealthCheckView(APIView):
    """Service health check endpoint.

    Returns the health status of the application including
    database and cache connectivity.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request: Request) -> Any:
        """Check service health.

        Returns:
            Standardized success response with health status details.
        """
        health_data: dict[str, Any] = {
            "status": "ok",
            "version": settings.APP_VERSION,
            "database": self._check_database(),
            "redis": self._check_redis(),
        }

        logger.info("Health check: %s", health_data["status"])
        return success_response(
            data=health_data,
            message="Service is healthy.",
        )

    def _check_database(self) -> str:
        """Check database connectivity."""
        try:
            connection.ensure_connection()
            return "connected"
        except Exception:
            logger.exception("Database health check failed")
            return "disconnected"

    def _check_redis(self) -> str:
        """Check Redis cache connectivity."""
        try:
            cache.set("health_check", "ok", timeout=10)
            result = cache.get("health_check")
            if result == "ok":
                return "connected"
            return "disconnected"
        except Exception:
            logger.exception("Redis health check failed")
            return "disconnected"


# =============================================================================
# Authentication Views (Sprint 1)
# =============================================================================


class LoginView(APIView):
    """Login with email and password, returns JWT tokens.

    POST /api/v1/auth/login/
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request: Request) -> Any:
        """Authenticate user and return JWT tokens.

        Args:
            request: Contains email and password.

        Returns:
            Success response with access/refresh tokens and user data.
        """
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = AuthService.login(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        return success_response(
            data=data,
            message=MSG_LOGIN_SUCCESS,
        )


class LogoutView(APIView):
    """Blacklist the refresh token (logout).

    POST /api/v1/auth/logout/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Any:
        """Blacklist the provided refresh token.

        Args:
            request: Contains the refresh token.

        Returns:
            Success response confirming logout.
        """
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        AuthService.logout(
            refresh_token=serializer.validated_data["refresh"],
        )

        return success_response(
            message=MSG_LOGOUT_SUCCESS,
        )


class RefreshTokenView(APIView):
    """Refresh an access token using a valid refresh token.

    POST /api/v1/auth/refresh/
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request: Request) -> Any:
        """Refresh the access token.

        Args:
            request: Contains the refresh token.

        Returns:
            Success response with new access and refresh tokens.
        """
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = AuthService.refresh_token(
            refresh_token=serializer.validated_data["refresh"],
        )

        return success_response(
            data=data,
            message=MSG_REFRESH_SUCCESS,
        )


class CurrentUserView(APIView):
    """Get or update the current user's profile.

    GET  /api/v1/auth/me/
    PATCH /api/v1/auth/me/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Any:
        """Return the current user's profile.

        Returns:
            Success response with user profile data.
        """
        serializer = UserProfileSerializer(request.user)
        return success_response(data=serializer.data)

    def patch(self, request: Request) -> Any:
        """Update the current user's profile.

        Args:
            request: Contains fields to update (full_name, phone).

        Returns:
            Success response with updated profile data.
        """
        serializer = UpdateProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = UserService.update_profile(
            user=request.user,
            **serializer.validated_data,
        )

        output_serializer = UserProfileSerializer(user)
        return success_response(
            data=output_serializer.data,
            message=MSG_PROFILE_UPDATED,
        )


class ChangePasswordView(APIView):
    """Change the current user's password.

    POST /api/v1/auth/change-password/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Any:
        """Change the authenticated user's password.

        Args:
            request: Contains old_password, new_password, confirm_password.

        Returns:
            Success response confirming password change.
        """
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        AuthService.change_password(
            user=request.user,
            old_password=serializer.validated_data["old_password"],
            new_password=serializer.validated_data["new_password"],
            confirm_password=serializer.validated_data["confirm_password"],
        )

        return success_response(
            message=MSG_PASSWORD_CHANGED,
        )


# =============================================================================
# RBAC Management Views (Sprint 1)
# =============================================================================


class RoleListCreateView(APIView):
    """List all roles or create a new role.

    GET  /api/v1/roles/     — requires view:role permission
    POST /api/v1/roles/     — requires create:role permission
    """

    permission_classes = [IsAuthenticated, HasPermission]

    def get_required_permission(self, request: Request) -> dict[str, str]:
        """Return the required permission based on HTTP method."""
        if request.method == "POST":
            return {"action": "create", "resource": "role"}
        return {"action": "view", "resource": "role"}

    def get(self, request: Request) -> Any:
        """List all roles.

        Returns:
            Success response with paginated list of roles.
        """
        self.required_permission = {"action": "view", "resource": "role"}
        roles = RoleSelector.get_all_roles()
        serializer = RoleListSerializer(roles, many=True)
        return success_response(data=serializer.data)

    def post(self, request: Request) -> Any:
        """Create a new role.

        Args:
            request: Contains name, description, permission_ids.

        Returns:
            Success response with the created role data.
        """
        self.required_permission = {"action": "create", "resource": "role"}
        serializer = CreateRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        role = RoleService.create_role(
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description", ""),
            permission_ids=serializer.validated_data.get("permission_ids"),
        )

        output_serializer = RoleDetailSerializer(role)
        return success_response(
            data=output_serializer.data,
            message=MSG_ROLE_CREATED,
            status_code=status.HTTP_201_CREATED,
        )

    def check_permissions(self, request: Request) -> None:
        """Override to set required_permission based on HTTP method."""
        if request.method == "POST":
            self.required_permission = {"action": "create", "resource": "role"}
        else:
            self.required_permission = {"action": "view", "resource": "role"}
        super().check_permissions(request)


class RoleDetailView(APIView):
    """Retrieve, update, or delete a role.

    GET    /api/v1/roles/{id}/  — requires view:role permission
    PATCH  /api/v1/roles/{id}/  — requires update:role permission
    DELETE /api/v1/roles/{id}/  — requires delete:role permission
    """

    permission_classes = [IsAuthenticated, HasPermission]

    def get(self, request: Request, role_id: str) -> Any:
        """Retrieve a role by ID.

        Args:
            request: The incoming request.
            role_id: The role's UUID.

        Returns:
            Success response with role details and permissions.
        """
        self.required_permission = {"action": "view", "resource": "role"}
        role = RoleSelector.get_role_by_id(role_id)
        if role is None:
            return error_response(
                message="Role not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = RoleDetailSerializer(role)
        return success_response(data=serializer.data)

    def patch(self, request: Request, role_id: str) -> Any:
        """Update a role.

        Args:
            request: Contains fields to update.
            role_id: The role's UUID.

        Returns:
            Success response with updated role data.
        """
        self.required_permission = {"action": "update", "resource": "role"}
        serializer = UpdateRoleSerializer(
            data=request.data,
            context={"role_id": role_id},
        )
        serializer.is_valid(raise_exception=True)

        role = RoleService.update_role(
            role_id=role_id,
            **serializer.validated_data,
        )

        output_serializer = RoleDetailSerializer(role)
        return success_response(
            data=output_serializer.data,
            message=MSG_ROLE_UPDATED,
        )

    def delete(self, request: Request, role_id: str) -> Any:
        """Delete a role.

        Args:
            request: The incoming request.
            role_id: The role's UUID.

        Returns:
            Success response confirming deletion.
        """
        self.required_permission = {"action": "delete", "resource": "role"}
        RoleService.delete_role(role_id=role_id)

        return success_response(
            message=MSG_ROLE_DELETED,
            status_code=status.HTTP_200_OK,
        )

    def check_permissions(self, request: Request) -> None:
        """Override to set required_permission based on HTTP method."""
        method_permission_map: dict[str, dict[str, str]] = {
            "GET": {"action": "view", "resource": "role"},
            "PATCH": {"action": "update", "resource": "role"},
            "DELETE": {"action": "delete", "resource": "role"},
        }
        self.required_permission = method_permission_map.get(
            request.method, {"action": "view", "resource": "role"}
        )
        super().check_permissions(request)


class PermissionListView(APIView):
    """List all available permissions.

    GET /api/v1/permissions/  — requires view:role permission
    """

    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = {"action": "view", "resource": "role"}

    def get(self, request: Request) -> Any:
        """List all permissions.

        Returns:
            Success response with all available permissions.
        """
        permissions = RoleSelector.get_all_permissions()
        serializer = PermissionSerializer(permissions, many=True)
        return success_response(data=serializer.data)
