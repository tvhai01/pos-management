"""
Authentication endpoint tests — Sprint 1.

Tests cover:
- Login (success, invalid credentials, inactive user, missing fields)
- Logout (success, without auth)
- Token refresh (success, invalid token)
- Current user (GET, PATCH, unauthenticated)
- Change password (success, wrong old password, mismatch)

All tests follow the Arrange-Act-Assert (AAA) pattern.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User


# =============================================================================
# Login Tests
# =============================================================================


@pytest.mark.django_db
class TestLogin:
    """Tests for POST /api/v1/auth/login/."""

    URL: str = "/api/v1/auth/login/"

    def test_login_success(
        self, api_client: APIClient, create_user: User, user_data: dict[str, str]
    ) -> None:
        """Test successful login returns tokens and user data."""
        # Arrange & Act
        response = api_client.post(
            self.URL,
            {"email": user_data["email"], "password": user_data["password"]},
        )
        data = response.json()

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert data["success"] is True
        assert data["message"] == "Login successful."
        assert "access" in data["data"]
        assert "refresh" in data["data"]
        assert data["data"]["user"]["email"] == user_data["email"]

    def test_login_invalid_credentials(self, api_client: APIClient) -> None:
        """Test login with wrong credentials returns 401."""
        # Arrange & Act
        response = api_client.post(
            self.URL,
            {"email": "nonexistent@example.com", "password": "WrongPass123!"},
        )
        data = response.json()

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert data["success"] is False

    def test_login_inactive_user(
        self, api_client: APIClient, inactive_user: User
    ) -> None:
        """Test login with inactive user returns 401."""
        # Arrange & Act
        response = api_client.post(
            self.URL,
            {"email": "inactive@example.com", "password": "InactivePass123!"},
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_fields(self, api_client: APIClient) -> None:
        """Test login without required fields returns 400."""
        # Arrange & Act
        response = api_client.post(self.URL, {})
        data = response.json()

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert data["success"] is False


# =============================================================================
# Logout Tests
# =============================================================================


@pytest.mark.django_db
class TestLogout:
    """Tests for POST /api/v1/auth/logout/."""

    URL: str = "/api/v1/auth/logout/"

    def test_logout_success(
        self,
        api_client: APIClient,
        create_user: User,
        user_tokens: dict[str, str],
    ) -> None:
        """Test successful logout blacklists the refresh token."""
        # Arrange
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {user_tokens['access']}"
        )

        # Act
        response = api_client.post(
            self.URL,
            {"refresh": user_tokens["refresh"]},
        )
        data = response.json()

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert data["success"] is True
        assert data["message"] == "Logout successful."

    def test_logout_without_auth(self, api_client: APIClient) -> None:
        """Test logout without authentication returns 401."""
        # Arrange & Act
        response = api_client.post(
            self.URL,
            {"refresh": "fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Token Refresh Tests
# =============================================================================


@pytest.mark.django_db
class TestRefreshToken:
    """Tests for POST /api/v1/auth/refresh/."""

    URL: str = "/api/v1/auth/refresh/"

    def test_refresh_token_success(
        self, api_client: APIClient, user_tokens: dict[str, str]
    ) -> None:
        """Test successful token refresh returns new tokens."""
        # Arrange & Act
        response = api_client.post(
            self.URL,
            {"refresh": user_tokens["refresh"]},
        )
        data = response.json()

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert data["success"] is True
        assert "access" in data["data"]

    def test_refresh_token_invalid(self, api_client: APIClient) -> None:
        """Test refresh with invalid token returns 401."""
        # Arrange & Act
        response = api_client.post(
            self.URL,
            {"refresh": "invalid-refresh-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Current User Tests
# =============================================================================


@pytest.mark.django_db
class TestCurrentUser:
    """Tests for GET/PATCH /api/v1/auth/me/."""

    URL: str = "/api/v1/auth/me/"

    def test_get_current_user(
        self, authenticated_client: APIClient, create_user: User
    ) -> None:
        """Test getting current user profile."""
        # Arrange & Act
        response = authenticated_client.get(self.URL)
        data = response.json()

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert data["success"] is True
        assert data["data"]["email"] == create_user.email
        assert data["data"]["full_name"] == create_user.full_name
        assert "roles" in data["data"]

    def test_get_current_user_unauthenticated(
        self, api_client: APIClient
    ) -> None:
        """Test getting current user without auth returns 401."""
        # Arrange & Act
        response = api_client.get(self.URL)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_current_user(
        self, authenticated_client: APIClient
    ) -> None:
        """Test updating current user profile."""
        # Arrange
        update_data = {
            "full_name": "Updated Name",
            "phone": "0987654321",
        }

        # Act
        response = authenticated_client.patch(
            self.URL, update_data, format="json"
        )
        data = response.json()

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert data["success"] is True
        assert data["data"]["full_name"] == "Updated Name"
        assert data["data"]["phone"] == "0987654321"


# =============================================================================
# Change Password Tests
# =============================================================================


@pytest.mark.django_db
class TestChangePassword:
    """Tests for POST /api/v1/auth/change-password/."""

    URL: str = "/api/v1/auth/change-password/"

    def test_change_password_success(
        self,
        authenticated_client: APIClient,
        create_user: User,
        user_data: dict[str, str],
    ) -> None:
        """Test successful password change."""
        # Arrange
        password_data = {
            "old_password": user_data["password"],
            "new_password": "NewSecurePass456!",
            "confirm_password": "NewSecurePass456!",
        }

        # Act
        response = authenticated_client.post(
            self.URL, password_data, format="json"
        )
        data = response.json()

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert data["success"] is True
        assert data["message"] == "Password changed successfully."

        # Verify old password no longer works
        create_user.refresh_from_db()
        assert create_user.check_password("NewSecurePass456!") is True
        assert create_user.check_password(user_data["password"]) is False

    def test_change_password_wrong_old(
        self, authenticated_client: APIClient
    ) -> None:
        """Test change password with incorrect old password."""
        # Arrange
        password_data = {
            "old_password": "WrongOldPass!",
            "new_password": "NewSecurePass456!",
            "confirm_password": "NewSecurePass456!",
        }

        # Act
        response = authenticated_client.post(
            self.URL, password_data, format="json"
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_mismatch(
        self,
        authenticated_client: APIClient,
        user_data: dict[str, str],
    ) -> None:
        """Test change password with mismatched new/confirm passwords."""
        # Arrange
        password_data = {
            "old_password": user_data["password"],
            "new_password": "NewSecurePass456!",
            "confirm_password": "DifferentPass789!",
        }

        # Act
        response = authenticated_client.post(
            self.URL, password_data, format="json"
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
