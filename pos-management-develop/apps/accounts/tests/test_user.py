"""
User management tests — Sprint 1.

Tests cover:
- User-Role relationship (M2M via UserRole through model)
- User serializer includes roles
- User profile serialization

All tests follow the Arrange-Act-Assert (AAA) pattern.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, User, UserRole
from apps.accounts.serializers import UserProfileSerializer
from apps.accounts.services import RoleService


# =============================================================================
# User-Role Relationship Tests
# =============================================================================


@pytest.mark.django_db
class TestUserRoleRelationship:
    """Tests for User-Role M2M relationships."""

    def test_user_roles_relationship(
        self, user_with_role: User, staff_role: Role
    ) -> None:
        """Test that user has roles accessible via M2M."""
        # Arrange — user_with_role already has staff_role
        # Act
        roles = user_with_role.roles.all()

        # Assert
        assert roles.count() == 1
        assert staff_role in roles

    def test_user_multiple_roles(
        self, create_user: User, staff_role: Role
    ) -> None:
        """Test that a user can have multiple roles."""
        # Arrange
        admin_role = Role.objects.create(
            name="Admin",
            description="Admin role",
        )
        UserRole.objects.create(user=create_user, role=staff_role)
        UserRole.objects.create(user=create_user, role=admin_role)

        # Act
        roles = create_user.roles.all()

        # Assert
        assert roles.count() == 2

    def test_assign_role_via_service(
        self, create_user: User, staff_role: Role
    ) -> None:
        """Test assigning a role via RoleService."""
        # Arrange & Act
        user_role = RoleService.assign_role_to_user(
            user=create_user,
            role_id=staff_role.id,
        )

        # Assert
        assert user_role.user == create_user
        assert user_role.role == staff_role
        assert create_user.roles.filter(id=staff_role.id).exists()

    def test_remove_role_via_service(
        self, user_with_role: User, staff_role: Role
    ) -> None:
        """Test removing a role via RoleService."""
        # Arrange — user_with_role already has staff_role
        # Act
        RoleService.remove_role_from_user(
            user=user_with_role,
            role_id=staff_role.id,
        )

        # Assert
        assert user_with_role.roles.count() == 0


# =============================================================================
# User Serializer Tests
# =============================================================================


@pytest.mark.django_db
class TestUserSerializer:
    """Tests for User serialization."""

    def test_user_serializer_includes_roles(
        self, user_with_role: User
    ) -> None:
        """Test that serialized user contains role names."""
        # Arrange & Act
        serializer = UserProfileSerializer(user_with_role)
        data = serializer.data

        # Assert
        assert "roles" in data
        assert "Staff" in data["roles"]

    def test_user_serializer_fields(
        self, create_user: User
    ) -> None:
        """Test that serializer includes all expected fields."""
        # Arrange & Act
        serializer = UserProfileSerializer(create_user)
        data = serializer.data

        # Assert
        expected_fields = {
            "id", "email", "full_name", "phone",
            "is_active", "roles", "date_joined",
            "created_at", "updated_at",
        }
        assert set(data.keys()) == expected_fields

    def test_user_serializer_read_only_fields(
        self, create_user: User
    ) -> None:
        """Test that read-only fields cannot be updated via serializer."""
        # Arrange
        data = {"email": "hacked@example.com", "full_name": "Valid Name"}
        serializer = UserProfileSerializer(
            create_user, data=data, partial=True
        )

        # Act
        serializer.is_valid()
        if serializer.is_valid():
            user = serializer.save()
            # Assert — email should NOT have changed
            assert user.email != "hacked@example.com"
