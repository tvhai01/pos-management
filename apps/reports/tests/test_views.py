"""Tests for the Report JSON API — permissions, validation, CSV export."""

from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.invoices.constants import InvoiceStatus
from apps.invoices.models import Invoice
from apps.payments.constants import (
    PaymentMethod,
    PaymentStatus,
    Provider,
    TransactionType,
)
from apps.payments.models import Payment, PaymentTransaction


@pytest.mark.django_db
class TestRevenueReportView:
    URL = "/api/v1/reports/revenue/"

    def test_requires_authentication(self, api_client: APIClient):
        response = api_client.get(self.URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_without_permission_is_forbidden(
        self, authenticated_client: APIClient
    ):
        response = authenticated_client.get(self.URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_view_permission_grants_access(
        self, authenticated_view_only_report_client: APIClient
    ):
        response = authenticated_view_only_report_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "total_revenue" in response.data["data"]

    def test_superuser_bypasses_rbac(self, superuser_client: APIClient):
        response = superuser_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK

    def test_inverted_date_range_is_rejected(
        self, authenticated_report_client: APIClient
    ):
        response = authenticated_report_client.get(
            self.URL, {"date_from": "2026-09-07", "date_to": "2026-09-01"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "date_from" in response.data["errors"]

    def test_defaults_to_30_day_range_when_no_dates_given(
        self, authenticated_report_client: APIClient
    ):
        response = authenticated_report_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert data["date_from"] is not None
        assert data["date_to"] is not None


@pytest.mark.django_db
class TestRevenueReportExportView:
    URL = "/api/v1/reports/revenue/export/"

    def test_view_permission_alone_is_not_enough_to_export(
        self, authenticated_view_only_report_client: APIClient
    ):
        response = authenticated_view_only_report_client.get(self.URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_export_permission_returns_csv(
        self, authenticated_report_client: APIClient
    ):
        response = authenticated_report_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"].startswith("text/csv")
        assert "attachment" in response["Content-Disposition"]

    def test_superuser_bypasses_rbac(self, superuser_client: APIClient):
        response = superuser_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTopSellingProductsReportView:
    URL = "/api/v1/reports/products/top-selling/"

    def test_top_n_over_max_is_rejected(self, authenticated_report_client: APIClient):
        response = authenticated_report_client.get(self.URL, {"top_n": 500})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_sort_by_is_rejected(self, authenticated_report_client: APIClient):
        response = authenticated_report_client.get(
            self.URL, {"sort_by": "not-a-choice"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_valid_request_returns_list(self, authenticated_report_client: APIClient):
        response = authenticated_report_client.get(
            self.URL, {"top_n": "5", "sort_by": "quantity"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data["data"], list)


@pytest.mark.django_db
class TestTopSellingProductsExportView:
    URL = "/api/v1/reports/products/top-selling/export/"

    def test_requires_export_permission(
        self, authenticated_view_only_report_client: APIClient
    ):
        response = authenticated_view_only_report_client.get(self.URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_csv(self, authenticated_report_client: APIClient):
        response = authenticated_report_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"].startswith("text/csv")


@pytest.mark.django_db
class TestInventoryReportView:
    URL = "/api/v1/reports/inventory/"

    def test_requires_permission(self, authenticated_client: APIClient):
        response = authenticated_client.get(self.URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_expected_shape(self, authenticated_report_client: APIClient):
        response = authenticated_report_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert "out_of_stock_count" in data
        assert "low_stock_products" in data


@pytest.mark.django_db
class TestInventoryReportExportView:
    URL = "/api/v1/reports/inventory/export/"

    def test_requires_export_permission(
        self, authenticated_view_only_report_client: APIClient
    ):
        response = authenticated_view_only_report_client.get(self.URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_csv(self, authenticated_report_client: APIClient):
        response = authenticated_report_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"].startswith("text/csv")


@pytest.mark.django_db
class TestPaymentBreakdownReportView:
    URL = "/api/v1/reports/payments/breakdown/"

    def test_requires_permission(self, authenticated_client: APIClient):
        response = authenticated_client.get(self.URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_expected_shape(self, authenticated_report_client: APIClient):
        response = authenticated_report_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert "by_payment_method" in data
        assert "by_provider" in data


@pytest.mark.django_db
class TestPaymentBreakdownExportView:
    URL = "/api/v1/reports/payments/breakdown/export/"

    def test_requires_export_permission(
        self, authenticated_view_only_report_client: APIClient
    ):
        response = authenticated_view_only_report_client.get(self.URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_csv(self, authenticated_report_client: APIClient):
        response = authenticated_report_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"].startswith("text/csv")

    def test_csv_rows_include_status_breakdown(
        self, authenticated_report_client: APIClient, create_customer, create_user: User
    ):
        invoice = Invoice.objects.create(
            invoice_number="INV-EXPORT-TEST",
            customer=create_customer,
            subtotal=Decimal("100"),
            total_amount=Decimal("100"),
            status=InvoiceStatus.PENDING_PAYMENT,
            created_by=create_user,
            updated_by=create_user,
        )
        payment = Payment.objects.create(
            invoice=invoice,
            reference="PAY-EXPORT-TEST",
            amount=Decimal("100"),
            payment_method=PaymentMethod.QR,
            status=PaymentStatus.SUCCESS,
            processed_at=timezone.now(),
            created_by=create_user,
            updated_by=create_user,
        )
        PaymentTransaction.objects.create(
            payment=payment,
            invoice=invoice,
            provider=Provider.SEPAY,
            transaction_type=TransactionType.PAYMENT,
            amount=Decimal("100"),
            status=PaymentStatus.SUCCESS,
            payment_method=PaymentMethod.QR,
            processed_at=timezone.now(),
            created_by=create_user,
            updated_by=create_user,
        )

        response = authenticated_report_client.get(self.URL)
        text = response.content.decode("utf-8-sig")
        assert "SUCCESS" in text
        assert "100" in text


@pytest.mark.django_db
class TestCustomerReportView:
    URL = "/api/v1/reports/customers/"

    def test_requires_permission(self, authenticated_client: APIClient):
        response = authenticated_client.get(self.URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_top_n_over_max_is_rejected(self, authenticated_report_client: APIClient):
        response = authenticated_report_client.get(self.URL, {"top_n": 999})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_returns_expected_shape(self, authenticated_report_client: APIClient):
        response = authenticated_report_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert "top_customers" in data
        assert "new_customers_count" in data


@pytest.mark.django_db
class TestCustomerReportExportView:
    URL = "/api/v1/reports/customers/export/"

    def test_requires_export_permission(
        self, authenticated_view_only_report_client: APIClient
    ):
        response = authenticated_view_only_report_client.get(self.URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_csv(self, authenticated_report_client: APIClient):
        response = authenticated_report_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"].startswith("text/csv")
