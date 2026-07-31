"""
JSON API root endpoint tests.

This view (`config.views.HomeView`) lives in `config/` (project-level, not
owned by any single app), so its tests live in the project-level `tests/`
package rather than under an `apps/<app>/tests/` directory. It's mounted at
`/api/v1/` — `/` is now the session-authenticated dashboard UI, tested
separately in `apps/dashboard/tests/test_dashboard.py`.

All tests follow the Arrange-Act-Assert (AAA) pattern.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestApiRootEndpoint:
    """Tests for GET /api/v1/."""

    URL: str = "/api/v1/"

    def test_api_root_returns_200(self, api_client: APIClient) -> None:
        """Test that the API root is reachable without auth."""
        # Arrange & Act
        response = api_client.get(self.URL)

        # Assert
        assert response.status_code == status.HTTP_200_OK

    def test_api_root_response_format(self, api_client: APIClient) -> None:
        """Test that the API root response follows the standard envelope."""
        # Arrange & Act
        response = api_client.get(self.URL)
        data = response.json()

        # Assert
        assert data["success"] is True
        assert "modules" in data["data"]
        assert data["data"]["service"] == "POS Management System"

    def test_api_root_lists_all_modules(self, api_client: APIClient) -> None:
        """Test that every shipped feature module is listed."""
        # Arrange & Act
        response = api_client.get(self.URL)
        modules = response.json()["data"]["modules"]

        # Assert
        for key in ("health", "auth", "rbac", "customers", "admin"):
            assert key in modules
            assert "base_url" in modules[key]

    def test_api_root_no_auth_required(self, api_client: APIClient) -> None:
        """Test that the API root doesn't require authentication."""
        # Arrange & Act
        response = api_client.get(self.URL)

        # Assert
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
