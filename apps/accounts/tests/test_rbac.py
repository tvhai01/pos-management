"""
RBAC model and permission tests — Sprint 1.

Tests cover:
- Permission model (creation, unique constraint, str representation)
- Role model (creation, permission assignment)
- UserRole (assignment, unique constraint)
- PermissionSelector (user_has_permission, superuser bypass)
- RBAC API endpoints (list roles, create role, permission enforcement)

All tests follow the Arrange-Act-Assert (AAA) pattern.
"""

import pytest
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.constants import PermissionAction, PermissionResource
from apps.accounts.models import Permission, Role, User, UserRole
from apps.accounts.selectors import PermissionSelector


# =============================================================================
# Permission Model Tests
# =============================================================================


@pytest.mark.django_db
class TestPermissionModel:
    """Tests for the Permission model."""

    def test_create_permission(self) -> None:
        """Test creating a permission with action-resource pattern."""
        # Arrange & Act
        permission = Permission.objects.create(
            name="Create User",
            action=PermissionAction.CREATE,
            resource=PermissionResource.USER,
        )

        # Assert
        assert permission.name == "Create User"
        assert permission.action == PermissionAction.CREATE
        assert permission.resource == PermissionResource.USER

    def test_permission_str_representation(self) -> None:
        """Test permission __str__ returns readable label."""
        # Arrange & Act
        permission = Permission.objects.create(
            name="View Product",
            action=PermissionAction.VIEW,
            resource=PermissionResource.PRODUCT,
        )

        # Assert
        assert str(permission) == "View Product"

    def test_permission_unique_action_resource(self) -> None:
        """Test that duplicate action-resource pairs raise IntegrityError."""
        # Arrange
        Permission.objects.create(
            name="Create User",
            action=PermissionAction.CREATE,
            resource=PermissionResource.USER,
        )

        # Act & Assert
        with pytest.raises(IntegrityError):
            Permission.objects.create(
                name="Create User Duplicate",
                action=PermissionAction.CREATE,
                resource=PermissionResource.USER,
            )


# =============================================================================
# Role Model Tests
# =============================================================================


@pytest.mark.django_db
class TestRoleModel:
    """Tests for the Role model."""

    def test_create_role(self) -> None:
        """Test creating a role."""
        # Arrange & Act
        role = Role.objects.create(
            name="Manager",
            description="Store manager role",
        )

        # Assert
        assert role.name == "Manager"
        assert role.is_active is True

    def test_role_with_permissions(
        self, staff_role: Role, all_role_permissions: list[Permission]
    ) -> None:
        """Test role has assigned permissions."""
        # Arrange — fixtures handle setup
        # Act
        permissions = staff_role.permissions.all()

        # Assert
        assert permissions.count() == len(all_role_permissions)

    def test_role_str_representation(self) -> None:
        """Test role __str__ returns the role name."""
        # Arrange & Act
        role = Role.objects.create(name="Cashier")

        # Assert
        assert str(role) == "Cashier"


# =============================================================================
# UserRole Tests
# =============================================================================


@pytest.mark.django_db
class TestUserRole:
    """Tests for the UserRole through model."""

    def test_assign_role_to_user(
        self, create_user: User, staff_role: Role
    ) -> None:
        """Test assigning a role to a user."""
        # Arrange & Act
        user_role = UserRole.objects.create(
            user=create_user, role=staff_role
        )

        # Assert
        assert user_role.user == create_user
        assert user_role.role == staff_role
        assert create_user.roles.count() == 1

    def test_user_role_unique_constraint(
        self, user_with_role: User, staff_role: Role
    ) -> None:
        """Test that duplicate user-role assignments raise IntegrityError."""
        # Arrange — user_with_role already has staff_role
        # Act & Assert
        with pytest.raises(IntegrityError):
            UserRole.objects.create(user=user_with_role, role=staff_role)

    def test_user_role_names_property(
        self, user_with_role: User
    ) -> None:
        """Test that User.role_names returns active role names."""
        # Arrange — user_with_role has Staff role
        # Act
        role_names = user_with_role.role_names

        # Assert
        assert "Staff" in role_names


# =============================================================================
# PermissionSelector Tests
# =============================================================================


@pytest.mark.django_db
class TestPermissionSelector:
    """Tests for the PermissionSelector."""

    def test_user_has_permission(
        self, user_with_role: User
    ) -> None:
        """Test that user with role has the expected permission."""
        # Arrange — user_with_role has Staff role with view:role permission
        # Act
        result = PermissionSelector.user_has_permission(
            user=user_with_role,
            action=PermissionAction.VIEW,
            resource=PermissionResource.ROLE,
        )

        # Assert
        assert result is True

    def test_user_without_permission(
        self, create_user: User
    ) -> None:
        """Test that user without role does not have permission."""
        # Arrange — create_user has no roles
        # Act
        result = PermissionSelector.user_has_permission(
            user=create_user,
            action=PermissionAction.CREATE,
            resource=PermissionResource.USER,
        )

        # Assert
        assert result is False

    def test_superuser_bypasses_rbac(
        self, create_superuser: User
    ) -> None:
        """Test that superuser bypasses all RBAC checks."""
        # Arrange — superuser has no explicit roles
        # Act
        result = PermissionSelector.user_has_permission(
            user=create_superuser,
            action=PermissionAction.DELETE,
            resource=PermissionResource.USER,
        )

        # Assert
        assert result is True

    def test_inactive_role_no_permission(
        self, user_with_role: User, staff_role: Role
    ) -> None:
        """Test that inactive role doesn't grant permissions."""
        # Arrange
        staff_role.is_active = False
        staff_role.save()

        # Act
        result = PermissionSelector.user_has_permission(
            user=user_with_role,
            action=PermissionAction.VIEW,
            resource=PermissionResource.ROLE,
        )

        # Assert
        assert result is False


# =============================================================================
# RBAC API Endpoint Tests
# =============================================================================


@pytest.mark.django_db
class TestRoleEndpoints:
    """Tests for the Role API endpoints."""

    LIST_URL: str = "/api/v1/roles/"

    def test_list_roles_with_permission(
        self,
        authenticated_staff_client: APIClient,
        staff_role: Role,
    ) -> None:
        """Test listing roles with view:role permission."""
        # Arrange & Act
        response = authenticated_staff_client.get(self.LIST_URL)
        data = response.json()

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_list_roles_without_permission(
        self, authenticated_client: APIClient
    ) -> None:
        """Test listing roles without permission returns 403."""
        # Arrange — authenticated_client has no roles
        # Act
        response = authenticated_client.get(self.LIST_URL)

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_role_with_permission(
        self,
        authenticated_staff_client: APIClient,
        view_role_permission: Permission,
    ) -> None:
        """Test creating a role with create:role permission."""
        # Arrange
        role_data = {
            "name": "New Role",
            "description": "A test role",
            "permission_ids": [str(view_role_permission.id)],
        }

        # Act
        response = authenticated_staff_client.post(
            self.LIST_URL, role_data, format="json"
        )
        data = response.json()

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        assert data["success"] is True
        assert data["data"]["name"] == "New Role"

    def test_superuser_can_manage_roles(
        self, superuser_client: APIClient
    ) -> None:
        """Test that superuser can access role management."""
        # Arrange & Act
        response = superuser_client.get(self.LIST_URL)

        # Assert
        assert response.status_code == status.HTTP_200_OK

    def test_delete_role_with_users_fails(
        self,
        superuser_client: APIClient,
        staff_role: Role,
        user_with_role: User,
    ) -> None:
        """Test that deleting a role with assigned users fails."""
        # Arrange
        url = f"{self.LIST_URL}{staff_role.id}/"

        # Act
        response = superuser_client.delete(url)

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPermissionEndpoints:
    """Tests for the Permission API endpoints."""

    URL: str = "/api/v1/permissions/"

    def test_list_permissions(
        self,
        authenticated_staff_client: APIClient,
        all_role_permissions: list[Permission],
    ) -> None:
        """Test listing all permissions."""
        # Arrange & Act
        response = authenticated_staff_client.get(self.URL)
        data = response.json()

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert data["success"] is True
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= len(all_role_permissions)
