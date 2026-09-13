"""
Customer model, service, selector, and API tests — Sprint 2.

Tests cover:
- Customer model (creation, str, unique constraints, soft delete)
- CustomerSelector (lookup, code/phone existence checks)
- CustomerService (create, update, soft delete)
- Customer API endpoints (create, list, search, filter, update,
  delete, permission enforcement)

All tests follow the Arrange-Act-Assert (AAA) pattern.
"""

import pytest
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APIClient

from apps.customers.constants import CustomerStatus
from apps.customers.exceptions import CustomerNotFoundError
from apps.customers.models import Customer
from apps.customers.selectors import CustomerSelector
from apps.customers.services import CustomerService

# =============================================================================
# Customer Model Tests
# =============================================================================


@pytest.mark.django_db
class TestCustomerModel:
    """Tests for the Customer model."""

    def test_create_customer(self, customer_data: dict[str, str]) -> None:
        """Test creating a customer with required fields."""
        # Arrange & Act
        customer = Customer.objects.create(**customer_data)

        # Assert
        assert customer.customer_code == customer_data["customer_code"]
        assert customer.full_name == customer_data["full_name"]
        assert customer.status == CustomerStatus.ACTIVE
        assert customer.is_deleted is False

    def test_customer_str_representation(self, create_customer: Customer) -> None:
        """Test customer __str__ returns code and name."""
        # Arrange — create_customer fixture
        # Act & Assert
        assert str(create_customer) == (
            f"{create_customer.customer_code} — {create_customer.full_name}"
        )

    def test_duplicate_customer_code_raises_integrity_error(
        self, create_customer: Customer
    ) -> None:
        """Test that duplicate customer_code raises IntegrityError."""
        # Arrange — create_customer already has code CUS000001
        # Act & Assert
        with pytest.raises(IntegrityError):
            Customer.objects.create(
                customer_code=create_customer.customer_code,
                full_name="Duplicate Customer",
                phone="0909999999",
            )

    def test_duplicate_phone_raises_integrity_error(
        self, create_customer: Customer
    ) -> None:
        """Test that duplicate phone raises IntegrityError."""
        # Arrange — create_customer already has phone 0901234567
        # Act & Assert
        with pytest.raises(IntegrityError):
            Customer.objects.create(
                customer_code="CUS000099",
                full_name="Duplicate Phone Customer",
                phone=create_customer.phone,
            )

    def test_soft_deleted_customer_excluded_from_default_manager(
        self, create_customer: Customer
    ) -> None:
        """Test that soft-deleted customers are hidden from `objects`."""
        # Arrange
        create_customer.is_deleted = True
        create_customer.save(update_fields=["is_deleted"])

        # Act & Assert
        assert not Customer.objects.filter(id=create_customer.id).exists()
        assert Customer.all_objects.filter(id=create_customer.id).exists()


# =============================================================================
# CustomerSelector Tests
# =============================================================================


@pytest.mark.django_db
class TestCustomerSelector:
    """Tests for the CustomerSelector."""

    def test_get_customer_by_id(self, create_customer: Customer) -> None:
        """Test retrieving a customer by UUID."""
        # Arrange & Act
        result = CustomerSelector.get_customer_by_id(create_customer.id)

        # Assert
        assert result == create_customer

    def test_get_customer_by_id_not_found(self) -> None:
        """Test that a non-existent UUID returns None."""
        # Arrange & Act
        result = CustomerSelector.get_customer_by_id(
            "00000000-0000-0000-0000-000000000000"
        )

        # Assert
        assert result is None

    def test_get_customer_by_code(self, create_customer: Customer) -> None:
        """Test retrieving a customer by customer_code."""
        # Arrange & Act
        result = CustomerSelector.get_customer_by_code(create_customer.customer_code)

        # Assert
        assert result == create_customer

    def test_code_exists(self, create_customer: Customer) -> None:
        """Test code_exists returns True for an existing code."""
        # Arrange & Act & Assert
        assert CustomerSelector.code_exists(create_customer.customer_code) is True
        assert CustomerSelector.code_exists("CUS999999") is False

    def test_code_exists_excludes_self(self, create_customer: Customer) -> None:
        """Test code_exists excludes the given customer ID."""
        # Arrange & Act
        result = CustomerSelector.code_exists(
            create_customer.customer_code, exclude_id=create_customer.id
        )

        # Assert
        assert result is False

    def test_phone_exists(self, create_customer: Customer) -> None:
        """Test phone_exists returns True for an existing phone."""
        # Arrange & Act & Assert
        assert CustomerSelector.phone_exists(create_customer.phone) is True
        assert CustomerSelector.phone_exists("0999999999") is False


# =============================================================================
# CustomerService Tests
# =============================================================================


@pytest.mark.django_db
class TestCustomerService:
    """Tests for the CustomerService."""

    def test_create_customer(self, customer_data: dict[str, str]) -> None:
        """Test creating a customer via the service layer."""
        # Arrange & Act
        customer = CustomerService.create_customer(**customer_data)

        # Assert
        assert customer.id is not None
        assert customer.customer_code == customer_data["customer_code"]

    def test_update_customer(self, create_customer: Customer) -> None:
        """Test updating a customer's full_name."""
        # Arrange & Act
        updated = CustomerService.update_customer(
            customer_id=create_customer.id,
            full_name="Updated Name",
        )

        # Assert
        assert updated.full_name == "Updated Name"

    def test_update_nonexistent_customer_raises(self) -> None:
        """Test that updating a missing customer raises CustomerNotFoundError."""
        # Arrange & Act & Assert
        with pytest.raises(CustomerNotFoundError):
            CustomerService.update_customer(
                customer_id="00000000-0000-0000-0000-000000000000",
                full_name="Ghost",
            )

    def test_delete_customer_soft_deletes(self, create_customer: Customer) -> None:
        """Test that deleting a customer sets is_deleted and deleted_at."""
        # Arrange & Act
        CustomerService.delete_customer(customer_id=create_customer.id)
        create_customer.refresh_from_db()

        # Assert
        assert create_customer.is_deleted is True
        assert create_customer.deleted_at is not None
        assert not Customer.objects.filter(id=create_customer.id).exists()

    def test_delete_nonexistent_customer_raises(self) -> None:
        """Test that deleting a missing customer raises CustomerNotFoundError."""
        # Arrange & Act & Assert
        with pytest.raises(CustomerNotFoundError):
            CustomerService.delete_customer(
                customer_id="00000000-0000-0000-0000-000000000000"
            )


# =============================================================================
# Customer API — Create/List Endpoint Tests
# =============================================================================


@pytest.mark.django_db
class TestCustomerListCreateEndpoint:
    """Tests for POST/GET /api/v1/customers/."""

    URL: str = "/api/v1/customers/"

    def test_create_customer_with_permission(
        self, authenticated_customer_client: APIClient, customer_data: dict[str, str]
    ) -> None:
        """Test creating a customer with create:customer permission."""
        # Arrange & Act
        response = authenticated_customer_client.post(
            self.URL, customer_data, format="json"
        )
        data = response.json()

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        assert data["success"] is True
        assert data["data"]["customer_code"] == customer_data["customer_code"]

    def test_create_customer_without_permission(
        self, authenticated_client: APIClient, customer_data: dict[str, str]
    ) -> None:
        """Test creating a customer without permission returns 403."""
        # Arrange & Act
        response = authenticated_client.post(self.URL, customer_data, format="json")

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_customer_duplicate_code_fails(
        self,
        authenticated_customer_client: APIClient,
        create_customer: Customer,
        customer_data: dict[str, str],
    ) -> None:
        """Test creating a customer with a duplicate code returns 400."""
        # Arrange — customer_data uses the same code as create_customer
        payload = {**customer_data, "phone": "0912345678"}

        # Act
        response = authenticated_customer_client.post(self.URL, payload, format="json")

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_customer_duplicate_phone_fails(
        self,
        authenticated_customer_client: APIClient,
        create_customer: Customer,
        customer_data: dict[str, str],
    ) -> None:
        """Test creating a customer with a duplicate phone returns 400."""
        # Arrange
        payload = {**customer_data, "customer_code": "CUS000777"}

        # Act
        response = authenticated_customer_client.post(self.URL, payload, format="json")

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_customer_invalid_phone_format_fails(
        self, authenticated_customer_client: APIClient, customer_data: dict[str, str]
    ) -> None:
        """Test creating a customer with a malformed phone returns 400."""
        # Arrange
        payload = {**customer_data, "phone": "abc123"}

        # Act
        response = authenticated_customer_client.post(self.URL, payload, format="json")

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_customers_with_permission(
        self, authenticated_customer_client: APIClient, create_customer: Customer
    ) -> None:
        """Test listing customers returns a paginated envelope."""
        # Arrange & Act
        response = authenticated_customer_client.get(self.URL)
        data = response.json()

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert data["success"] is True
        assert "results" in data["data"]
        assert data["data"]["count"] >= 1

    def test_list_customers_without_permission(
        self, authenticated_client: APIClient
    ) -> None:
        """Test listing customers without permission returns 403."""
        # Arrange & Act
        response = authenticated_client.get(self.URL)

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_search_customer_by_code(
        self, authenticated_customer_client: APIClient, create_customer: Customer
    ) -> None:
        """Test searching customers by customer_code."""
        # Arrange & Act
        response = authenticated_customer_client.get(
            self.URL, {"search": create_customer.customer_code}
        )
        data = response.json()["data"]["results"]

        # Assert
        assert len(data) == 1
        assert data[0]["customer_code"] == create_customer.customer_code

    def test_search_customer_by_phone(
        self, authenticated_customer_client: APIClient, create_customer: Customer
    ) -> None:
        """Test searching customers by phone."""
        # Arrange & Act
        response = authenticated_customer_client.get(
            self.URL, {"search": create_customer.phone}
        )
        data = response.json()["data"]["results"]

        # Assert
        assert len(data) == 1

    def test_search_customer_no_match(
        self, authenticated_customer_client: APIClient, create_customer: Customer
    ) -> None:
        """Test searching with a term that matches nothing."""
        # Arrange & Act
        response = authenticated_customer_client.get(
            self.URL, {"search": "no-such-customer"}
        )
        data = response.json()["data"]["results"]

        # Assert
        assert len(data) == 0

    def test_filter_customer_by_status(
        self, authenticated_customer_client: APIClient, create_customer: Customer
    ) -> None:
        """Test filtering customers by status."""
        # Arrange & Act
        response = authenticated_customer_client.get(
            self.URL, {"status": CustomerStatus.ACTIVE}
        )
        data = response.json()["data"]["results"]

        # Assert
        assert all(c["status"] == CustomerStatus.ACTIVE for c in data)

    def test_superuser_can_create_customer(
        self, superuser_client: APIClient, customer_data: dict[str, str]
    ) -> None:
        """Test that superuser bypasses RBAC for customer creation."""
        # Arrange & Act
        response = superuser_client.post(self.URL, customer_data, format="json")

        # Assert
        assert response.status_code == status.HTTP_201_CREATED


# =============================================================================
# Customer API — Detail Endpoint Tests
# =============================================================================


@pytest.mark.django_db
class TestCustomerDetailEndpoint:
    """Tests for GET/PUT/DELETE /api/v1/customers/{id}/."""

    def url(self, customer_id: object) -> str:
        """Build the detail URL for a given customer ID."""
        return f"/api/v1/customers/{customer_id}/"

    def test_get_customer_detail(
        self, authenticated_customer_client: APIClient, create_customer: Customer
    ) -> None:
        """Test retrieving a customer's detail."""
        # Arrange & Act
        response = authenticated_customer_client.get(self.url(create_customer.id))
        data = response.json()

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert data["data"]["customer_code"] == create_customer.customer_code

    def test_get_customer_detail_not_found(
        self, authenticated_customer_client: APIClient
    ) -> None:
        """Test retrieving a non-existent customer returns 404."""
        # Arrange & Act
        response = authenticated_customer_client.get(
            self.url("00000000-0000-0000-0000-000000000000")
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_customer_with_permission(
        self, authenticated_customer_client: APIClient, create_customer: Customer
    ) -> None:
        """Test updating a customer with update:customer permission."""
        # Arrange
        payload = {"full_name": "Nguyen Van B", "note": "VIP customer"}

        # Act
        response = authenticated_customer_client.put(
            self.url(create_customer.id), payload, format="json"
        )
        data = response.json()

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert data["data"]["full_name"] == "Nguyen Van B"
        assert data["data"]["note"] == "VIP customer"

    def test_update_customer_without_permission(
        self, authenticated_client: APIClient, create_customer: Customer
    ) -> None:
        """Test updating a customer without permission returns 403."""
        # Arrange & Act
        response = authenticated_client.put(
            self.url(create_customer.id), {"full_name": "X"}, format="json"
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_customer_with_permission(
        self, authenticated_customer_client: APIClient, create_customer: Customer
    ) -> None:
        """Test soft-deleting a customer with delete:customer permission."""
        # Arrange & Act
        response = authenticated_customer_client.delete(self.url(create_customer.id))

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert not Customer.objects.filter(id=create_customer.id).exists()
        assert Customer.all_objects.filter(id=create_customer.id).exists()

    def test_delete_customer_without_permission(
        self, authenticated_client: APIClient, create_customer: Customer
    ) -> None:
        """Test deleting a customer without permission returns 403."""
        # Arrange & Act
        response = authenticated_client.delete(self.url(create_customer.id))

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Customer.objects.filter(id=create_customer.id).exists()

    def test_deleted_customer_not_retrievable(
        self, authenticated_customer_client: APIClient, create_customer: Customer
    ) -> None:
        """Test that a soft-deleted customer returns 404 afterwards."""
        # Arrange
        authenticated_customer_client.delete(self.url(create_customer.id))

        # Act
        response = authenticated_customer_client.get(self.url(create_customer.id))

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
