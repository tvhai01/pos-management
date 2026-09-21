"""
Dashboard app tests — session-authenticated admin UI.

Uses Django's test `client` fixture (real session auth via `client.login()`),
not DRF's `APIClient` — `force_authenticate` only patches `request.user` for
DRF views, not plain Django views rendered by `apps.dashboard`.

Tests cover:
- Login (render, success, wrong password, inactive user, already-logged-in)
- Logout
- Home/index (login required, module visibility by permission)
- Customer list/create/edit/delete via the dashboard UI, including
  permission enforcement (view/create/update/delete), mirroring the
  API test suite in apps/customers/tests/test_customer.py.

All tests follow the Arrange-Act-Assert (AAA) pattern.
"""

import uuid

import pytest
from django.test import Client

from apps.accounts.constants import PermissionAction, PermissionResource
from apps.accounts.models import Permission, Role, User, UserRole
from apps.customers.models import Customer
from apps.invoices.models import Invoice
from apps.orders.services import OrderService
from apps.product.models import Product

# =============================================================================
# Login / Logout
# =============================================================================


@pytest.mark.django_db
class TestLogin:
    """Tests for GET/POST /login/."""

    URL: str = "/login/"

    def test_login_page_renders(self, client: Client) -> None:
        """Test that the login page is reachable without auth."""
        # Arrange & Act
        response = client.get(self.URL)

        # Assert
        assert response.status_code == 200

    def test_login_success_redirects_to_index(
        self, client: Client, create_user: User, user_data: dict[str, str]
    ) -> None:
        """Test that valid credentials establish a session and redirect."""
        # Arrange & Act
        response = client.post(
            self.URL,
            {"email": user_data["email"], "password": user_data["password"]},
        )

        # Assert
        assert response.status_code == 302
        assert response.url == "/"

    def test_login_wrong_password_shows_error(
        self, client: Client, create_user: User, user_data: dict[str, str]
    ) -> None:
        """Test that a wrong password re-renders the form with an error."""
        # Arrange & Act
        response = client.post(
            self.URL, {"email": user_data["email"], "password": "WrongPass123!"}
        )

        # Assert
        assert response.status_code == 200
        assert "không đúng" in response.content.decode()

    def test_login_inactive_user_cannot_establish_session(
        self, client: Client, inactive_user: User
    ) -> None:
        """Test that a deactivated account can't log in."""
        # Arrange & Act
        response = client.post(
            self.URL,
            {"email": inactive_user.email, "password": "InactivePass123!"},
        )

        # Assert — no redirect (no session established), stays on login page
        assert response.status_code == 200

    def test_already_logged_in_redirects_away_from_login(
        self, client: Client, create_user: User, user_data: dict[str, str]
    ) -> None:
        """Test that a logged-in user visiting /login/ is bounced to index."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])

        # Act
        response = client.get(self.URL)

        # Assert
        assert response.status_code == 302


@pytest.mark.django_db
class TestLogout:
    """Tests for POST /logout/."""

    def test_logout_redirects_to_login(
        self, client: Client, create_user: User, user_data: dict[str, str]
    ) -> None:
        """Test that logging out ends the session and redirects to login."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])

        # Act
        response = client.post("/logout/")

        # Assert
        assert response.status_code == 302
        assert response.url == "/login/"


# =============================================================================
# Home / Index
# =============================================================================


@pytest.mark.django_db
class TestIndex:
    """Tests for GET /."""

    URL: str = "/"

    def test_requires_login(self, client: Client) -> None:
        """Test that an anonymous visit is redirected to login."""
        # Arrange & Act
        response = client.get(self.URL)

        # Assert
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_renders_when_logged_in(
        self, client: Client, create_user: User, user_data: dict[str, str]
    ) -> None:
        """Test that a logged-in user sees the dashboard home."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])

        # Act
        response = client.get(self.URL)

        # Assert
        assert response.status_code == 200

    def test_customers_module_available_with_permission(
        self,
        client: Client,
        user_with_customer_role: User,
        user_data: dict[str, str],
    ) -> None:
        """Test that the Customers module renders as a clickable link."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])

        # Act
        response = client.get(self.URL)
        html = response.content.decode()

        # Assert — the Customers module renders a real link, not the
        # "no access" placeholder (Django Admin's card still shows the
        # placeholder for this non-staff user, so we check the specific
        # customer-list URL rather than searching the whole page).
        assert "Khách hàng" in html
        assert "/customers/" in html


# =============================================================================
# Customer List
# =============================================================================


@pytest.mark.django_db
class TestCustomerListView:
    """Tests for GET /customers/."""

    URL: str = "/customers/"

    def test_requires_login(self, client: Client) -> None:
        """Test that an anonymous visit is redirected to login."""
        # Arrange & Act
        response = client.get(self.URL)

        # Assert
        assert response.status_code == 302

    def test_requires_permission(
        self, client: Client, create_user: User, user_data: dict[str, str]
    ) -> None:
        """Test that a logged-in user without view:customer gets a 403 page."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])

        # Act
        response = client.get(self.URL)

        # Assert
        assert response.status_code == 403

    def test_lists_customers_with_permission(
        self,
        client: Client,
        user_with_customer_role: User,
        user_data: dict[str, str],
        create_customer: Customer,
    ) -> None:
        """Test that customers render in the table for an authorized user."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])

        # Act
        response = client.get(self.URL)

        # Assert
        assert response.status_code == 200
        assert create_customer.customer_code in response.content.decode()

    def test_search_filters_results(
        self,
        client: Client,
        user_with_customer_role: User,
        user_data: dict[str, str],
        create_customer: Customer,
    ) -> None:
        """Test that an unrelated search term excludes the customer."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])

        # Act
        response = client.get(self.URL, {"search": "no-such-customer"})

        # Assert
        assert create_customer.customer_code not in response.content.decode()


# =============================================================================
# Customer Create
# =============================================================================


@pytest.mark.django_db
class TestCustomerCreateView:
    """Tests for GET/POST /customers/create/."""

    URL: str = "/customers/create/"

    def test_requires_permission(
        self, client: Client, create_user: User, user_data: dict[str, str]
    ) -> None:
        """Test that create:customer is required."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])

        # Act
        response = client.get(self.URL)

        # Assert
        assert response.status_code == 403

    def test_creates_customer(
        self,
        client: Client,
        user_with_customer_role: User,
        user_data: dict[str, str],
        customer_data: dict[str, str],
    ) -> None:
        """Test that a valid form submission creates the customer."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])
        payload = {**customer_data, "status": "active"}

        # Act
        response = client.post(self.URL, payload)

        # Assert
        assert response.status_code == 302
        assert Customer.objects.filter(
            customer_code=customer_data["customer_code"]
        ).exists()

    def test_duplicate_code_shows_form_error(
        self,
        client: Client,
        user_with_customer_role: User,
        user_data: dict[str, str],
        create_customer: Customer,
        customer_data: dict[str, str],
    ) -> None:
        """Test that a duplicate customer_code is rejected with a form error."""
        # Arrange — create_customer already uses customer_data's code
        client.login(email=user_data["email"], password=user_data["password"])
        payload = {**customer_data, "phone": "0999999999", "status": "active"}

        # Act
        response = client.post(self.URL, payload)

        # Assert
        assert response.status_code == 200
        assert "đã tồn tại" in response.content.decode()


# =============================================================================
# Customer Edit
# =============================================================================


@pytest.mark.django_db
class TestCustomerEditView:
    """Tests for GET/POST /customers/{id}/edit/."""

    def url(self, customer_id: object) -> str:
        """Build the edit URL for a given customer ID."""
        return f"/customers/{customer_id}/edit/"

    def test_requires_permission(
        self,
        client: Client,
        create_user: User,
        user_data: dict[str, str],
        create_customer: Customer,
    ) -> None:
        """Test that update:customer is required."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])

        # Act
        response = client.get(self.url(create_customer.id))

        # Assert
        assert response.status_code == 403

    def test_updates_customer(
        self,
        client: Client,
        user_with_customer_role: User,
        user_data: dict[str, str],
        create_customer: Customer,
        customer_data: dict[str, str],
    ) -> None:
        """Test that a valid form submission updates the customer."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])
        payload = {**customer_data, "full_name": "Updated Name", "status": "active"}

        # Act
        response = client.post(self.url(create_customer.id), payload)
        create_customer.refresh_from_db()

        # Assert
        assert response.status_code == 302
        assert create_customer.full_name == "Updated Name"


# =============================================================================
# Customer Delete
# =============================================================================


@pytest.mark.django_db
class TestCustomerDeleteView:
    """Tests for GET/POST /customers/{id}/delete/."""

    def url(self, customer_id: object) -> str:
        """Build the delete URL for a given customer ID."""
        return f"/customers/{customer_id}/delete/"

    def test_requires_permission(
        self,
        client: Client,
        create_user: User,
        user_data: dict[str, str],
        create_customer: Customer,
    ) -> None:
        """Test that delete:customer is required."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])

        # Act
        response = client.get(self.url(create_customer.id))

        # Assert
        assert response.status_code == 403

    def test_confirm_page_renders(
        self,
        client: Client,
        user_with_customer_role: User,
        user_data: dict[str, str],
        create_customer: Customer,
    ) -> None:
        """Test that the delete confirmation page renders (no delete on GET)."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])

        # Act
        response = client.get(self.url(create_customer.id))

        # Assert
        assert response.status_code == 200
        assert Customer.objects.filter(id=create_customer.id).exists()

    def test_deletes_customer_on_post(
        self,
        client: Client,
        user_with_customer_role: User,
        user_data: dict[str, str],
        create_customer: Customer,
    ) -> None:
        """Test that POST soft-deletes the customer and redirects."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])

        # Act
        response = client.post(self.url(create_customer.id))

        # Assert
        assert response.status_code == 302
        assert not Customer.objects.filter(id=create_customer.id).exists()
        assert Customer.all_objects.filter(id=create_customer.id).exists()


# =============================================================================
# Invoice Print
# =============================================================================


@pytest.fixture
def view_invoice_permission() -> Permission:
    """Create a 'view invoice' permission."""
    return Permission.objects.create(
        name="View Invoice",
        action=PermissionAction.VIEW,
        resource=PermissionResource.INVOICE,
    )


@pytest.fixture
def user_with_invoice_role(
    create_user: User, view_invoice_permission: Permission
) -> User:
    """Assign `view:invoice` to the standard test user."""
    role = Role.objects.create(name="Invoice Viewer")
    role.permissions.set([view_invoice_permission])
    UserRole.objects.create(user=create_user, role=role)
    return create_user


@pytest.fixture
def invoice_for_print(
    create_user: User, create_customer: Customer, product: Product
) -> Invoice:
    """Create an invoice linked to an order with one line item."""
    _, invoice = OrderService.create_order(
        customer=create_customer,
        items=[{"product_id": product.id, "quantity": 2}],
        created_by=create_user,
    )
    return invoice


@pytest.mark.django_db
class TestInvoicePrintView:
    """Tests for GET /invoices/{id}/print/."""

    def url(self, invoice_id: object) -> str:
        """Build the print URL for a given invoice ID."""
        return f"/invoices/{invoice_id}/print/"

    def test_requires_login(self, client: Client, invoice_for_print: Invoice) -> None:
        """Test that an anonymous visit is redirected to login."""
        # Arrange & Act
        response = client.get(self.url(invoice_for_print.id))

        # Assert
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_requires_permission(
        self,
        client: Client,
        create_user: User,
        user_data: dict[str, str],
        invoice_for_print: Invoice,
    ) -> None:
        """Test that view:invoice is required."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])

        # Act
        response = client.get(self.url(invoice_for_print.id))

        # Assert
        assert response.status_code == 403

    def test_renders_receipt(
        self,
        client: Client,
        user_with_invoice_role: User,
        user_data: dict[str, str],
        invoice_for_print: Invoice,
    ) -> None:
        """Test that the receipt renders with invoice and item details."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])

        # Act
        response = client.get(self.url(invoice_for_print.id))

        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        assert "HÓA ĐƠN BÁN HÀNG" in content
        assert invoice_for_print.invoice_number in content
        assert "Mineral Water" in content

    def test_missing_invoice_redirects(
        self,
        client: Client,
        user_with_invoice_role: User,
        user_data: dict[str, str],
    ) -> None:
        """Test that an unknown invoice id redirects to the invoice list."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])

        # Act
        response = client.get(self.url(uuid.uuid4()))

        # Assert
        assert response.status_code == 302
        assert response.url == "/invoices/"
