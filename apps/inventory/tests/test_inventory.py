"""Inventory model, selector, service, API, RBAC, and Dashboard tests."""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.inventory.constants import StockMovementType, StockStatus
from apps.inventory.exceptions import (
    InsufficientStockError,
    InvalidStockQuantityError,
    InventoryProductNotFoundError,
    NoStockChangeError,
)
from apps.inventory.models import Inventory, StockMovement
from apps.inventory.selectors import InventorySelector, StockMovementSelector
from apps.inventory.services import InventoryService
from apps.inventory.validators import parse_quantity
from apps.product.models import Product
from apps.product.services import ProductService


@pytest.mark.django_db
class TestInventoryModels:
    """Inventory persistence constraints and computed state."""

    def test_inventory_uses_uuid_audit_and_one_product(
        self, inventory: Inventory, product: Product
    ) -> None:
        """Test stable UUID, audit timestamps, and readable label."""
        assert inventory.id is not None
        assert inventory.created_at is not None
        assert inventory.product == product
        assert str(inventory) == "SP001: 0.000"

    def test_stock_status_transitions(self, inventory: Inventory) -> None:
        """Test out-of-stock, low-stock, and in-stock calculations."""
        assert inventory.stock_status == StockStatus.OUT_OF_STOCK
        assert inventory.stock_status_label == "Hết hàng"

        inventory.quantity = Decimal("5")
        assert inventory.stock_status == StockStatus.LOW_STOCK

        inventory.quantity = Decimal("11")
        assert inventory.stock_status == StockStatus.IN_STOCK

    def test_negative_balance_is_rejected_by_database(
        self, inventory: Inventory
    ) -> None:
        """Test the database backstop against negative stock."""
        with pytest.raises(IntegrityError), transaction.atomic():
            Inventory.objects.filter(id=inventory.id).update(quantity=Decimal("-1"))

    def test_movement_is_immutable(self, inventory: Inventory) -> None:
        """Test that ledger rows cannot be edited or deleted through models."""
        _, movement = InventoryService.record_movement(
            product_id=inventory.product_id,
            movement_type=StockMovementType.INBOUND,
            quantity="2",
        )
        movement.note = "changed"

        with pytest.raises(ValidationError):
            movement.save()
        with pytest.raises(ValidationError):
            movement.delete()


@pytest.mark.django_db
class TestInventorySelectors:
    """Read-only balance and movement queries."""

    def test_get_inventory_and_malformed_id(self, inventory: Inventory) -> None:
        """Test Inventory lookup success and malformed/missing IDs."""
        assert (
            InventorySelector.get_inventory_by_product_id(inventory.product_id)
            == inventory
        )
        assert InventorySelector.get_inventory_by_product_id(uuid4()) is None
        assert InventorySelector.get_inventory_by_product_id("invalid") is None

    def test_search_and_stock_status_filter(self, inventory: Inventory) -> None:
        """Test Product search and computed out-of-stock filtering."""
        results = InventorySelector.search_inventories(
            search="mineral",
            stock_status=StockStatus.OUT_OF_STOCK,
        )
        assert list(results) == [inventory]

    def test_product_movement_history(self, inventory: Inventory) -> None:
        """Test history is restricted to the requested Product."""
        _, movement = InventoryService.record_movement(
            product_id=inventory.product_id,
            movement_type=StockMovementType.INBOUND,
            quantity="3",
            reference_code="PO-001",
        )
        assert list(
            StockMovementSelector.get_product_movements(inventory.product_id)
        ) == [movement]


@pytest.mark.django_db
class TestInventoryServices:
    """Transactional stock mutation business rules."""

    def test_initialize_inventory_is_idempotent(
        self, inventory: Inventory, product: Product
    ) -> None:
        """Test repeated initialization does not create duplicates."""
        same_inventory = InventoryService.initialize_inventory(product)
        assert same_inventory.id == inventory.id
        assert Inventory.objects.filter(product=product).count() == 1

    def test_inbound_and_outbound_create_balanced_ledger(
        self, inventory: Inventory, create_user: User
    ) -> None:
        """Test signed deltas and before/after balances."""
        updated, inbound = InventoryService.record_movement(
            product_id=inventory.product_id,
            movement_type=StockMovementType.INBOUND,
            quantity="10.5554",
            reference_code=" PO-001 ",
            created_by=create_user,
        )
        updated, outbound = InventoryService.record_movement(
            product_id=inventory.product_id,
            movement_type=StockMovementType.OUTBOUND,
            quantity="2.555",
            created_by=create_user,
        )

        assert updated.quantity == Decimal("8.000")
        assert inbound.quantity_delta == Decimal("10.555")
        assert inbound.reference_code == "PO-001"
        assert outbound.quantity_delta == Decimal("-2.555")
        assert outbound.balance_before == Decimal("10.555")
        assert outbound.balance_after == Decimal("8.000")
        assert outbound.created_by == create_user

    def test_insufficient_outbound_rolls_back(self, inventory: Inventory) -> None:
        """Test an invalid outbound changes neither balance nor ledger."""
        with pytest.raises(InsufficientStockError):
            InventoryService.record_movement(
                product_id=inventory.product_id,
                movement_type=StockMovementType.OUTBOUND,
                quantity="1",
            )

        inventory.refresh_from_db()
        assert inventory.quantity == 0
        assert StockMovement.objects.count() == 0

    def test_adjustment_uses_target_balance(self, inventory: Inventory) -> None:
        """Test adjustment quantity means final desired stock."""
        InventoryService.record_movement(
            product_id=inventory.product_id,
            movement_type=StockMovementType.INBOUND,
            quantity="5",
        )
        updated, adjustment = InventoryService.record_movement(
            product_id=inventory.product_id,
            movement_type=StockMovementType.ADJUSTMENT,
            quantity="2",
        )
        assert updated.quantity == Decimal("2.000")
        assert adjustment.quantity_delta == Decimal("-3.000")

    def test_adjustment_must_change_balance(self, inventory: Inventory) -> None:
        """Test no-op adjustments are rejected."""
        with pytest.raises(NoStockChangeError):
            InventoryService.record_movement(
                product_id=inventory.product_id,
                movement_type=StockMovementType.ADJUSTMENT,
                quantity="0",
            )

    @pytest.mark.parametrize("quantity", ["", "abc", "-1", "Infinity"])
    def test_invalid_quantities_are_rejected(
        self, inventory: Inventory, quantity: str
    ) -> None:
        """Test invalid input never reaches the database."""
        with pytest.raises(InvalidStockQuantityError):
            InventoryService.record_movement(
                product_id=inventory.product_id,
                movement_type=StockMovementType.INBOUND,
                quantity=quantity,
            )

    def test_deleted_product_cannot_receive_movements(
        self, inventory: Inventory, product: Product
    ) -> None:
        """Test soft-deleted Products retain history but reject new changes."""
        product.soft_delete()
        product.save(update_fields=["is_deleted", "deleted_at"])

        with pytest.raises(InventoryProductNotFoundError):
            InventoryService.record_movement(
                product_id=product.id,
                movement_type=StockMovementType.INBOUND,
                quantity="1",
            )
        assert InventorySelector.get_inventory_by_product_id(product.id) is None
        assert (
            InventorySelector.get_inventory_by_product_id(
                product.id, include_deleted_product=True
            )
            == inventory
        )

    def test_update_threshold(self, inventory: Inventory, create_user: User) -> None:
        """Test non-negative warning threshold update and audit actor."""
        updated = InventoryService.update_low_stock_threshold(
            product_id=inventory.product_id,
            threshold="3.5",
            updated_by=create_user,
        )
        assert updated.low_stock_threshold == Decimal("3.500")
        assert updated.updated_by == create_user

    def test_product_service_initializes_inventory(
        self, product_category, create_user: User
    ) -> None:
        """Test normal Product creation establishes a zero balance."""
        product = ProductService.create_product(
            sku="INV-AUTO",
            name="Auto Inventory",
            category_id=product_category.id,
            cost_price=Decimal("1"),
            selling_price=Decimal("2"),
            created_by=create_user,
        )
        inventory = Inventory.objects.get(product=product)
        assert inventory.quantity == 0
        assert inventory.created_by == create_user


@pytest.mark.django_db
class TestInventoryApi:
    """JWT-compatible API behavior and RBAC enforcement."""

    LIST_URL = "/api/v1/inventory/"
    MOVEMENT_URL = "/api/v1/inventory/movements/"

    def test_authentication_and_permission_required(
        self, authenticated_client: APIClient
    ) -> None:
        """Test 401 for anonymous and 403 without Inventory permission."""
        assert (
            APIClient().get(self.LIST_URL).status_code == status.HTTP_401_UNAUTHORIZED
        )
        assert (
            authenticated_client.get(self.LIST_URL).status_code
            == status.HTTP_403_FORBIDDEN
        )

    def test_list_detail_search_and_filter(
        self,
        authenticated_inventory_client: APIClient,
        inventory: Inventory,
    ) -> None:
        """Test paginated balance list and Product detail."""
        listed = authenticated_inventory_client.get(
            self.LIST_URL,
            {"search": "SP001", "product__status": "active"},
        )
        detail = authenticated_inventory_client.get(
            f"{self.LIST_URL}{inventory.product_id}/"
        )
        assert listed.status_code == status.HTTP_200_OK
        assert listed.json()["data"]["count"] == 1
        assert detail.status_code == status.HTTP_200_OK
        assert detail.json()["data"]["quantity"] == "0.000"

    def test_create_movements_and_list_history(
        self,
        authenticated_inventory_client: APIClient,
        inventory: Inventory,
    ) -> None:
        """Test inbound API response and searchable history list."""
        created = authenticated_inventory_client.post(
            self.MOVEMENT_URL,
            {
                "product_id": str(inventory.product_id),
                "movement_type": "inbound",
                "quantity": "4.250",
                "reference_code": "PO-API",
            },
            format="json",
        )
        history = authenticated_inventory_client.get(
            self.MOVEMENT_URL,
            {"search": "PO-API", "movement_type": "inbound"},
        )
        assert created.status_code == status.HTTP_201_CREATED
        assert created.json()["data"]["inventory"]["quantity"] == "4.250"
        assert history.status_code == status.HTTP_200_OK
        assert history.json()["data"]["count"] == 1

    def test_insufficient_stock_returns_conflict(
        self,
        authenticated_inventory_client: APIClient,
        inventory: Inventory,
    ) -> None:
        """Test outbound business conflict uses HTTP 409 envelope."""
        response = authenticated_inventory_client.post(
            self.MOVEMENT_URL,
            {
                "product_id": str(inventory.product_id),
                "movement_type": "outbound",
                "quantity": "1",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["success"] is False

    def test_update_threshold_and_missing_detail(
        self,
        authenticated_inventory_client: APIClient,
        inventory: Inventory,
    ) -> None:
        """Test threshold update and missing Product response."""
        updated = authenticated_inventory_client.patch(
            f"{self.LIST_URL}{inventory.product_id}/threshold/",
            {"low_stock_threshold": "2.000"},
            format="json",
        )
        missing = authenticated_inventory_client.get(f"{self.LIST_URL}{uuid4()}/")
        assert updated.status_code == status.HTTP_200_OK
        assert updated.json()["data"]["low_stock_threshold"] == "2.000"
        assert missing.status_code == status.HTTP_404_NOT_FOUND

    def test_superuser_bypasses_inventory_rbac(
        self, superuser_client: APIClient, inventory: Inventory
    ) -> None:
        """Test superusers can view Inventory without explicit role rows."""
        response = superuser_client.get(self.LIST_URL)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestInventoryDashboard:
    """Session-authenticated Inventory Dashboard flow."""

    def test_pages_require_login(self, client: Client, inventory: Inventory) -> None:
        """Test anonymous Dashboard requests redirect to login."""
        assert client.get("/inventory/").status_code == status.HTTP_302_FOUND
        assert (
            client.get(f"/inventory/{inventory.product_id}/").status_code
            == status.HTTP_302_FOUND
        )

    def test_pages_require_permission(
        self, client: Client, create_user: User, inventory: Inventory
    ) -> None:
        """Test authenticated users without Inventory rights receive 403."""
        client.force_login(create_user)
        assert client.get("/inventory/").status_code == status.HTTP_403_FORBIDDEN

    def test_inventory_list_renders_selected_stock_and_recent_movement(
        self,
        client: Client,
        user_with_inventory_role: User,
        inventory: Inventory,
    ) -> None:
        """Test the master-detail list exposes balance and recent ledger rows."""
        # Arrange
        client.force_login(user_with_inventory_role)
        _, movement = InventoryService.record_movement(
            product_id=inventory.product_id,
            movement_type=StockMovementType.INBOUND,
            quantity="4",
        )

        # Act
        response = client.get("/inventory/", {"selected": str(inventory.product_id)})

        # Assert
        html = response.content.decode()
        assert response.status_code == status.HTTP_200_OK
        assert response.context["selected_inventory"] == inventory
        assert list(response.context["recent_movements"]) == [movement]
        assert "Chi tiết tồn kho" in html
        assert "Lịch sử biến động gần đây" in html

    def test_list_detail_movement_and_threshold_flow(
        self,
        client: Client,
        user_with_inventory_role: User,
        inventory: Inventory,
    ) -> None:
        """Test the primary session-authenticated Inventory workflow."""
        client.force_login(user_with_inventory_role)
        listed = client.get("/inventory/?stock_status=out_of_stock")
        detail = client.get(f"/inventory/{inventory.product_id}/")
        movement = client.post(
            f"/inventory/{inventory.product_id}/movement/",
            {
                "movement_type": "inbound",
                "quantity": "6",
                "reference_code": "PO-UI",
                "note": "Dashboard receipt",
            },
        )
        threshold = client.post(
            f"/inventory/{inventory.product_id}/threshold/",
            {"low_stock_threshold": "3"},
        )

        inventory.refresh_from_db()
        assert listed.status_code == status.HTTP_200_OK
        assert detail.status_code == status.HTTP_200_OK
        assert "10 Chai" in detail.content.decode()
        assert "10.000 Chai" not in detail.content.decode()
        assert movement.status_code == status.HTTP_302_FOUND
        assert threshold.status_code == status.HTTP_302_FOUND
        assert inventory.quantity == Decimal("6.000")
        assert inventory.low_stock_threshold == Decimal("3.000")


def test_parse_quantity_helper() -> None:
    """Test Decimal normalization without touching Django models."""
    assert parse_quantity("1.2345") == Decimal("1.235")
    assert parse_quantity("0") is None
    assert parse_quantity("0", allow_zero=True) == Decimal("0.000")
