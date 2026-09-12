"""
Staff (User Management) tests — Sprint 5.

Tests cover:
- Create staff user (success, duplicate email, permission checks)
- List/search staff users
- Update staff user (role assignment/removal)
- Deactivate staff user (soft, reversible)

All tests follow the Arrange-Act-Assert (AAA) pattern.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, User

TEST_PASSWORD: str = "Pass123456!"  # noqa: S105 — test fixture value, not a secret


# =============================================================================
# Create User Tests
# =============================================================================


@pytest.mark.django_db
class TestCreateUser:
    """Tests for POST /api/v1/users/."""

    def test_create_user_success(
        self,
        authenticated_user_management_client: APIClient,
        staff_role: Role,
    ) -> None:
        """Test creating a staff user with a role assigned."""
        # Arrange
        payload = {
            "email": "newstaff@example.com",
            "full_name": "New Staff",
            "password": "SecurePass123!",
            "phone": "0909999999",
            "role_ids": [str(staff_role.id)],
        }

        # Act
        response = authenticated_user_management_client.post(
            "/api/v1/users/", payload, format="json"
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        created_user = User.objects.get(email="newstaff@example.com")
        assert created_user.check_password("SecurePass123!")
        assert staff_role.name in created_user.role_names

    def test_create_user_duplicate_email(
        self,
        authenticated_user_management_client: APIClient,
        create_user: User,
    ) -> None:
        """Test that creating a user with an existing email fails."""
        # Arrange
        payload = {
            "email": create_user.email,
            "full_name": "Duplicate",
            "password": "SecurePass123!",
        }

        # Act
        response = authenticated_user_management_client.post(
            "/api/v1/users/", payload, format="json"
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_user_without_permission(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test that a user without create:user permission is forbidden."""
        # Arrange
        payload = {
            "email": "forbidden@example.com",
            "full_name": "Forbidden",
            "password": "SecurePass123!",
        }

        # Act
        response = authenticated_client.post("/api/v1/users/", payload, format="json")

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_superuser_can_create_user(
        self,
        superuser_client: APIClient,
    ) -> None:
        """Test that a superuser bypasses RBAC and can create a user."""
        # Arrange
        payload = {
            "email": "superstaff@example.com",
            "full_name": "Super Staff",
            "password": "SecurePass123!",
        }

        # Act
        response = superuser_client.post("/api/v1/users/", payload, format="json")

        # Assert
        assert response.status_code == status.HTTP_201_CREATED


# =============================================================================
# List Users Tests
# =============================================================================


@pytest.mark.django_db
class TestListUsers:
    """Tests for GET /api/v1/users/."""

    def test_list_users_search(
        self,
        authenticated_user_management_client: APIClient,
        user_with_user_management_role: User,
    ) -> None:
        """Test searching users by email."""
        # Arrange
        User.objects.create_user(
            email="other@example.com",
            password=TEST_PASSWORD,
            full_name="Other Person",
        )

        # Act
        response = authenticated_user_management_client.get(
            "/api/v1/users/", {"search": "other@example.com"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        results = response.data["data"]["results"]
        assert len(results) == 1
        assert results[0]["email"] == "other@example.com"

    def test_list_users_filter_is_active(
        self,
        authenticated_user_management_client: APIClient,
        inactive_user: User,
    ) -> None:
        """Test filtering users by active status."""
        # Act
        response = authenticated_user_management_client.get(
            "/api/v1/users/", {"is_active": "false"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        emails = [row["email"] for row in response.data["data"]["results"]]
        assert inactive_user.email in emails

    def test_list_users_without_permission(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test that listing users without view:user permission is forbidden."""
        # Act
        response = authenticated_client.get("/api/v1/users/")

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Update User Tests
# =============================================================================


@pytest.mark.django_db
class TestUpdateUser:
    """Tests for PATCH /api/v1/users/{id}/."""

    def test_update_user_changes_roles(
        self,
        authenticated_user_management_client: APIClient,
        user_with_user_management_role: User,
        staff_role: Role,
    ) -> None:
        """Test that updating role_ids assigns and removes roles correctly."""
        # Arrange
        target_user = User.objects.create_user(
            email="target@example.com",
            password=TEST_PASSWORD,
            full_name="Target User",
        )
        extra_role = Role.objects.create(name="Extra Role")
        target_user.roles.add(extra_role)

        # Act — replace extra_role with staff_role
        response = authenticated_user_management_client.patch(
            f"/api/v1/users/{target_user.id}/",
            {"role_ids": [str(staff_role.id)]},
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        target_user.refresh_from_db()
        role_names = set(target_user.role_names)
        assert role_names == {staff_role.name}

    def test_update_user_without_permission(
        self,
        authenticated_client: APIClient,
        create_user: User,
    ) -> None:
        """Test that updating a user without update:user permission is forbidden."""
        # Act
        response = authenticated_client.patch(
            f"/api/v1/users/{create_user.id}/",
            {"full_name": "Changed"},
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Deactivate User Tests
# =============================================================================


@pytest.mark.django_db
class TestDeactivateUser:
    """Tests for DELETE /api/v1/users/{id}/."""

    def test_deactivate_user(
        self,
        authenticated_user_management_client: APIClient,
        user_with_user_management_role: User,
    ) -> None:
        """Test that deleting a user deactivates rather than hard-deletes it."""
        # Arrange
        target_user = User.objects.create_user(
            email="deactivate-me@example.com",
            password=TEST_PASSWORD,
            full_name="Deactivate Me",
        )

        # Act
        response = authenticated_user_management_client.delete(
            f"/api/v1/users/{target_user.id}/"
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        target_user.refresh_from_db()
        assert target_user.is_active is False
        assert User.objects.filter(id=target_user.id).exists()

    def test_deactivate_user_without_permission(
        self,
        authenticated_client: APIClient,
        create_user: User,
    ) -> None:
        """Test that deactivating without delete:user permission is forbidden."""
        # Act
        response = authenticated_client.delete(f"/api/v1/users/{create_user.id}/")

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
