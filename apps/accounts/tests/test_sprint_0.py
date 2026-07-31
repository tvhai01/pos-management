"""
Unit tests for the Accounts app — Sprint 0.

Tests cover:
- Custom User model creation (regular user and superuser).
- User model constraints (email uniqueness, required fields).
- Health check endpoint (response format and connectivity checks).

All tests follow the Arrange-Act-Assert (AAA) pattern.
"""

import pytest
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User


# =============================================================================
# User Model Tests
# =============================================================================


@pytest.mark.django_db
class TestUserModel:
    """Tests for the custom User model."""

    def test_create_user_with_email(
        self, user_data: dict[str, str]
    ) -> None:
        """Test creating a regular user with email-based auth."""
        # Arrange & Act
        user = User.objects.create_user(
            email=user_data["email"],
            password=user_data["password"],
            full_name=user_data["full_name"],
        )

        # Assert
        assert user.email == user_data["email"]
        assert user.full_name == user_data["full_name"]
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.check_password(user_data["password"]) is True

    def test_create_user_without_email_raises_error(self) -> None:
        """Test that creating a user without email raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="The email field is required."):
            User.objects.create_user(
                email="",
                password="SomePass123!",
                full_name="No Email User",
            )

    def test_create_superuser(self) -> None:
        """Test creating a superuser with correct flags."""
        # Arrange & Act
        superuser = User.objects.create_superuser(
            email="superadmin@example.com",
            password="SuperPass123!",
            full_name="Super Admin",
        )

        # Assert
        assert superuser.email == "superadmin@example.com"
        assert superuser.is_active is True
        assert superuser.is_staff is True
        assert superuser.is_superuser is True

    def test_create_superuser_without_is_staff_raises_error(self) -> None:
        """Test that superuser with is_staff=False raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Superuser must have is_staff=True."):
            User.objects.create_superuser(
                email="bad_superuser@example.com",
                password="SuperPass123!",
                full_name="Bad Superuser",
                is_staff=False,
            )

    def test_create_superuser_without_is_superuser_raises_error(self) -> None:
        """Test that superuser with is_superuser=False raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(
            ValueError, match="Superuser must have is_superuser=True."
        ):
            User.objects.create_superuser(
                email="bad_superuser@example.com",
                password="SuperPass123!",
                full_name="Bad Superuser",
                is_superuser=False,
            )

    def test_user_email_unique(self, create_user: User) -> None:
        """Test that duplicate email addresses raise IntegrityError."""
        # Arrange — create_user fixture already created a user
        # Act & Assert
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                email=create_user.email,
                password="AnotherPass123!",
                full_name="Duplicate User",
            )

    def test_user_str_representation(self, create_user: User) -> None:
        """Test that __str__ returns the email address."""
        # Arrange & Act
        result = str(create_user)

        # Assert
        assert result == create_user.email

    def test_user_email_normalized(self) -> None:
        """Test that email is normalized (domain lowercased)."""
        # Arrange & Act
        user = User.objects.create_user(
            email="Test@EXAMPLE.COM",
            password="NormalizePass123!",
            full_name="Normalize Test",
        )

        # Assert
        assert user.email == "Test@example.com"

    def test_user_short_name_property(self, create_user: User) -> None:
        """Test that short_name returns the first name."""
        # Arrange & Act
        result = create_user.short_name

        # Assert
        assert result == "Test"


# =============================================================================
# Health Check Endpoint Tests
# =============================================================================


@pytest.mark.django_db
class TestHealthCheckEndpoint:
    """Tests for the GET /api/v1/health/ endpoint."""

    HEALTH_URL: str = "/api/v1/health/"

    def test_health_endpoint_returns_200(self, api_client: APIClient) -> None:
        """Test that the health check returns HTTP 200."""
        # Arrange & Act
        response = api_client.get(self.HEALTH_URL)

        # Assert
        assert response.status_code == status.HTTP_200_OK

    def test_health_response_format(self, api_client: APIClient) -> None:
        """Test that the health check response matches the standard format."""
        # Arrange & Act
        response = api_client.get(self.HEALTH_URL)
        data = response.json()

        # Assert
        assert data["success"] is True
        assert "message" in data
        assert "data" in data
        assert data["data"]["status"] == "ok"
        assert "version" in data["data"]
        assert "database" in data["data"]
        assert "redis" in data["data"]

    def test_health_check_reports_database_status(
        self, api_client: APIClient
    ) -> None:
        """Test that the health check reports database connectivity."""
        # Arrange & Act
        response = api_client.get(self.HEALTH_URL)
        data = response.json()

        # Assert
        assert data["data"]["database"] == "connected"

    def test_health_check_no_auth_required(self, api_client: APIClient) -> None:
        """Test that the health check does not require authentication."""
        # Arrange — api_client is unauthenticated
        # Act
        response = api_client.get(self.HEALTH_URL)

        # Assert
        assert response.status_code == status.HTTP_200_OK
