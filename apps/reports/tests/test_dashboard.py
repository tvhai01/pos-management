"""Tests for the session-authenticated Report dashboard screens."""

import pytest
from django.test import Client

from apps.accounts.models import User


@pytest.mark.django_db
class TestReportDashboard:
    URL = "/reports/"

    def test_redirects_anonymous_user_to_login(self, client: Client):
        response = client.get(self.URL)
        assert response.status_code == 302
        assert "/login/" in response["Location"]

    def test_forbidden_without_view_permission(
        self, client: Client, create_user: User, user_data: dict[str, str]
    ):
        client.login(email=user_data["email"], password=user_data["password"])
        response = client.get(self.URL)
        assert response.status_code == 403

    def test_renders_for_user_with_view_permission(
        self,
        client: Client,
        user_with_view_only_report_role: User,
        user_data: dict[str, str],
    ):
        client.login(email=user_data["email"], password=user_data["password"])
        response = client.get(self.URL)
        assert response.status_code == 200
        assert response.context["form"] is not None
        assert response.context["can_export"] is False

    def test_export_link_hidden_without_export_permission(
        self,
        client: Client,
        user_with_view_only_report_role: User,
        user_data: dict[str, str],
    ):
        client.login(email=user_data["email"], password=user_data["password"])
        response = client.get(self.URL)
        assert response.context["can_export"] is False


@pytest.mark.django_db
class TestReportExportViews:
    URL = "/reports/revenue/export/"

    def test_forbidden_without_export_permission(
        self,
        client: Client,
        user_with_view_only_report_role: User,
        user_data: dict[str, str],
    ):
        client.login(email=user_data["email"], password=user_data["password"])
        response = client.get(self.URL)
        assert response.status_code == 403

    def test_returns_csv_with_export_permission(
        self,
        client: Client,
        user_with_report_role: User,
        user_data: dict[str, str],
    ):
        client.login(email=user_data["email"], password=user_data["password"])
        response = client.get(self.URL)
        assert response.status_code == 200
        assert response["Content-Type"].startswith("text/csv")
