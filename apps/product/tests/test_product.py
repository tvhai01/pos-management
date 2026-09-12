"""Product/Category model, selector, service, API, and Dashboard tests."""

from decimal import Decimal
from uuid import uuid4

import pytest
from django.db import IntegrityError, transaction
from django.test import Client
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.product.exceptions import (
    CategoryHasProductsError,
    CategoryNotFoundError,
    ProductNotFoundError,
)
from apps.product.models import Category, Product
from apps.product.selectors import CategorySelector, ProductSelector
from apps.product.services import CategoryService, ProductService
from apps.product.validators import normalize_sku, parse_price


@pytest.mark.django_db
class TestProductModels:
    """Model constraints and soft-delete manager behavior."""

    def test_product_uses_uuid_and_audit_fields(self, product: Product) -> None:
        """Test that Product has stable UUID and audit timestamps."""
        # Arrange & Act
        label = str(product)

        # Assert
        assert product.id is not None
        assert product.created_at is not None
        assert label == "SP001 - Mineral Water"

    def test_category_string(self, product_category: Category) -> None:
        """Test the Category display label."""
        # Arrange & Act
        label = str(product_category)

        # Assert
        assert label == "Beverages"

    def test_sku_is_unique(self, product: Product) -> None:
        """Test that duplicate SKU values are rejected by PostgreSQL."""
        # Arrange, Act & Assert
        with pytest.raises(IntegrityError), transaction.atomic():
            Product.objects.create(
                sku=product.sku,
                name="Duplicate",
                cost_price=Decimal("1.00"),
                selling_price=Decimal("2.00"),
            )

    def test_invalid_price_relationship_is_rejected(self) -> None:
        """Test that selling price cannot be less than or equal to cost."""
        # Arrange, Act & Assert
        with pytest.raises(IntegrityError), transaction.atomic():
            Product.objects.create(
                sku="BADPRICE",
                name="Bad Price",
                cost_price=Decimal("100.00"),
                selling_price=Decimal("100.00"),
            )

    def test_soft_deleted_product_is_hidden(self, product: Product) -> None:
        """Test default/all manager behavior after a Product soft delete."""
        # Arrange
        product.soft_delete()
        product.save(update_fields=["is_deleted", "deleted_at"])

        # Act & Assert
        assert not Product.objects.filter(id=product.id).exists()
        assert Product.all_objects.filter(id=product.id).exists()

    def test_soft_deleted_category_is_hidden(self, product_category: Category) -> None:
        """Test default/all manager behavior after a Category soft delete."""
        # Arrange
        product_category.soft_delete()
        product_category.save(update_fields=["is_deleted", "deleted_at"])

        # Act & Assert
        assert not Category.objects.filter(id=product_category.id).exists()
        assert Category.all_objects.filter(id=product_category.id).exists()


@pytest.mark.django_db
class TestProductSelectors:
    """Read-only Product and Category selector behavior."""

    def test_product_selector_get_and_missing(self, product: Product) -> None:
        """Test Product lookup success and malformed/missing IDs."""
        # Arrange & Act
        found = ProductSelector.get_product_by_id(product.id)
        missing = ProductSelector.get_product_by_id(uuid4())
        malformed = ProductSelector.get_product_by_id("invalid")

        # Assert
        assert found == product
        assert missing is None
        assert malformed is None

    def test_product_search_filter_and_sort(
        self, product: Product, product_category: Category
    ) -> None:
        """Test dashboard search/category/status filters."""
        # Arrange & Act
        results = ProductSelector.search_products(
            search="SP001",
            category_id=str(product_category.id),
            status="active",
            sort="price_desc",
        )

        # Assert
        assert list(results) == [product]

    def test_product_sku_exists_includes_deleted(self, product: Product) -> None:
        """Test uniqueness checks include deleted rows and support exclusion."""
        # Arrange
        ProductService.delete_product(product.id)

        # Act & Assert
        assert ProductSelector.sku_exists("sp001") is True
        assert ProductSelector.sku_exists("SP001", exclude_id=product.id) is False
        assert ProductSelector.get_deleted_product_by_id(product.id) is not None

    def test_category_selector_search_and_counts(
        self, product: Product, product_category: Category
    ) -> None:
        """Test Category search and active Product annotation."""
        # Arrange & Act
        results = CategorySelector.search_categories(
            search="bever", has_products="yes", sort="most_products"
        )

        # Assert
        assert list(results) == [product_category]
        assert results[0].active_product_count == 1

    def test_category_selector_missing_and_name_uniqueness(
        self, product_category: Category
    ) -> None:
        """Test Category missing lookup and case-insensitive uniqueness."""
        # Arrange & Act
        missing = CategorySelector.get_category_by_id("invalid")

        # Assert
        assert missing is None
        assert CategorySelector.name_exists("beverages") is True
        assert (
            CategorySelector.name_exists("Beverages", exclude_id=product_category.id)
            is False
        )


@pytest.mark.django_db
class TestProductServices:
    """Transactional Product and Category business operations."""

    def test_create_and_update_product(
        self, product_data: dict, create_user: User
    ) -> None:
        """Test Product creation, SKU normalization, and mutable updates."""
        # Arrange & Act
        product = ProductService.create_product(
            **{**product_data, "sku": " sp-new "},
            created_by=create_user,
        )
        updated = ProductService.update_product(
            product.id,
            updated_by=create_user,
            name="Updated Product",
            category_id=None,
        )

        # Assert
        assert product.sku == "SP-NEW"
        assert updated.name == "Updated Product"
        assert updated.category is None
        assert updated.updated_by == create_user

    def test_create_product_with_missing_category_raises(
        self, product_data: dict
    ) -> None:
        """Test Product creation rejects an unavailable Category."""
        # Arrange
        payload = {**product_data, "category_id": uuid4(), "sku": "SP404"}

        # Act & Assert
        with pytest.raises(CategoryNotFoundError):
            ProductService.create_product(**payload)

    def test_update_and_delete_missing_product_raise(self) -> None:
        """Test missing Product service operations raise domain errors."""
        # Arrange
        missing_id = uuid4()

        # Act & Assert
        with pytest.raises(ProductNotFoundError):
            ProductService.update_product(missing_id, name="Missing")
        with pytest.raises(ProductNotFoundError):
            ProductService.delete_product(missing_id)
        with pytest.raises(ProductNotFoundError):
            ProductService.restore_product(missing_id)

    def test_delete_and_restore_product(self, product: Product) -> None:
        """Test Product soft deletion and restoration."""
        # Arrange & Act
        ProductService.delete_product(product.id)
        restored = ProductService.restore_product(product.id)

        # Assert
        assert restored.is_deleted is False
        assert restored.deleted_at is None

    def test_category_crud_and_missing(self, create_user: User) -> None:
        """Test Category create/update/delete/restore and missing update."""
        # Arrange & Act
        category = CategoryService.create_category("  Snacks  ", created_by=create_user)
        updated = CategoryService.update_category(
            category.id,
            updated_by=create_user,
            description="Quick food",
        )
        CategoryService.delete_category(category.id, deleted_by=create_user)
        restored = CategoryService.restore_category(
            category.id, restored_by=create_user
        )

        # Assert
        assert updated.name == "Snacks"
        assert restored.is_deleted is False
        with pytest.raises(CategoryNotFoundError):
            CategoryService.update_category(uuid4(), name="Missing")

    def test_category_with_product_cannot_be_deleted(
        self, product_category: Category, product: Product
    ) -> None:
        """Test referenced Category soft deletion is rejected."""
        # Arrange, Act & Assert
        with pytest.raises(CategoryHasProductsError):
            CategoryService.delete_category(product_category.id)


@pytest.mark.django_db
class TestProductApi:
    """Product REST API behavior, validation, pagination, and RBAC."""

    URL: str = "/api/v1/products/"

    def test_authentication_and_permission_required(
        self, api_client: APIClient, create_user: User
    ) -> None:
        """Test anonymous and no-role users cannot list Products."""
        # Arrange & Act
        anonymous = api_client.get(self.URL)
        api_client.force_authenticate(user=create_user)
        forbidden = api_client.get(self.URL)

        # Assert
        assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED
        assert forbidden.status_code == status.HTTP_403_FORBIDDEN

    def test_create_list_search_and_filter(
        self,
        authenticated_product_client: APIClient,
        product_category: Category,
    ) -> None:
        """Test Product creation and paginated search/filter list."""
        # Arrange
        payload = {
            "sku": "sp-api",
            "name": "API Product",
            "category_id": str(product_category.id),
            "unit": "piece",
            "cost_price": "10.00",
            "selling_price": "15.00",
            "status": "active",
        }

        # Act
        created = authenticated_product_client.post(self.URL, payload, format="json")
        listed = authenticated_product_client.get(
            self.URL,
            {"search": "SP-API", "status": "active", "page_size": "5"},
        )

        # Assert
        assert created.status_code == status.HTTP_201_CREATED
        assert created.json()["data"]["sku"] == "SP-API"
        assert listed.status_code == status.HTTP_200_OK
        assert listed.json()["data"]["count"] == 1

    def test_duplicate_sku_and_invalid_prices_fail(
        self, authenticated_product_client: APIClient, product: Product
    ) -> None:
        """Test Product input validation rejects duplicate SKU and bad prices."""
        # Arrange
        duplicate = {
            "sku": "sp001",
            "name": "Duplicate",
            "cost_price": "10.00",
            "selling_price": "20.00",
        }
        bad_price = {
            "sku": "SP-BAD",
            "name": "Bad",
            "cost_price": "20.00",
            "selling_price": "10.00",
        }

        # Act
        duplicate_response = authenticated_product_client.post(
            self.URL, duplicate, format="json"
        )
        bad_price_response = authenticated_product_client.post(
            self.URL, bad_price, format="json"
        )

        # Assert
        assert duplicate_response.status_code == status.HTTP_400_BAD_REQUEST
        assert bad_price_response.status_code == status.HTTP_400_BAD_REQUEST

    def test_detail_update_immutable_sku_and_soft_delete(
        self, authenticated_product_client: APIClient, product: Product
    ) -> None:
        """Test Product detail, update, immutable SKU, and soft deletion."""
        # Arrange
        url = f"{self.URL}{product.id}/"

        # Act
        detail = authenticated_product_client.get(url)
        updated = authenticated_product_client.patch(
            url, {"name": "Updated"}, format="json"
        )
        immutable = authenticated_product_client.patch(
            url, {"sku": "CHANGED"}, format="json"
        )
        deleted = authenticated_product_client.delete(url)
        missing = authenticated_product_client.get(url)

        # Assert
        assert detail.status_code == status.HTTP_200_OK
        assert updated.json()["data"]["name"] == "Updated"
        assert immutable.status_code == status.HTTP_400_BAD_REQUEST
        assert deleted.status_code == status.HTTP_200_OK
        assert missing.status_code == status.HTTP_404_NOT_FOUND
        assert Product.all_objects.get(id=product.id).is_deleted is True

    def test_superuser_bypasses_product_rbac(
        self, superuser_client: APIClient, product_data: dict
    ) -> None:
        """Test a superuser can create Product without a role."""
        # Arrange
        payload = {**product_data, "sku": "SP-SUPER"}

        # Act
        response = superuser_client.post(self.URL, payload, format="json")

        # Assert
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestCategoryApi:
    """Category REST API behavior and reference protection."""

    URL: str = "/api/v1/categories/"

    def test_category_create_update_and_delete(
        self, authenticated_product_client: APIClient
    ) -> None:
        """Test Category API lifecycle uses soft deletion."""
        # Arrange & Act
        created = authenticated_product_client.post(
            self.URL, {"name": "Snacks"}, format="json"
        )
        category_id = created.json()["data"]["id"]
        detail_url = f"{self.URL}{category_id}/"
        updated = authenticated_product_client.patch(
            detail_url, {"description": "Food"}, format="json"
        )
        deleted = authenticated_product_client.delete(detail_url)

        # Assert
        assert created.status_code == status.HTTP_201_CREATED
        assert updated.status_code == status.HTTP_200_OK
        assert deleted.status_code == status.HTTP_200_OK
        assert Category.all_objects.get(id=category_id).is_deleted is True

    def test_category_with_product_cannot_be_deleted(
        self,
        authenticated_product_client: APIClient,
        product_category: Category,
        product: Product,
    ) -> None:
        """Test Category delete returns conflict while Product references it."""
        # Arrange
        url = f"{self.URL}{product_category.id}/"

        # Act
        response = authenticated_product_client.delete(url)

        # Assert
        assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.django_db
class TestProductDashboard:
    """Session-authenticated Product Dashboard behavior."""

    def test_product_pages_require_login(self, client: Client) -> None:
        """Test Product, Category, and trash pages redirect anonymous users."""
        # Arrange & Act
        responses = [
            client.get("/products/"),
            client.get("/categories/"),
            client.get("/trash/"),
        ]

        # Assert
        assert all(response.status_code == 302 for response in responses)

    def test_product_pages_require_permission(
        self, client: Client, create_user: User, user_data: dict[str, str]
    ) -> None:
        """Test a logged-in no-role user receives a 403."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])

        # Act
        response = client.get("/products/")

        # Assert
        assert response.status_code == 403

    def test_product_list_renders_selected_product_inspector(
        self,
        client: Client,
        user_with_product_role: User,
        product: Product,
    ) -> None:
        """Test the master-detail list exposes the selected Product."""
        # Arrange
        client.force_login(user_with_product_role)

        # Act
        response = client.get("/products/", {"selected": str(product.id)})

        # Assert
        html = response.content.decode()
        assert response.status_code == status.HTTP_200_OK
        assert response.context["selected_product"] == product
        assert "Thông tin sản phẩm" in html
        assert product.sku in html

    def test_product_create_update_delete_restore_flow(
        self,
        client: Client,
        user_with_product_role: User,
        user_data: dict[str, str],
        product_category: Category,
    ) -> None:
        """Test the Product HTML form lifecycle through services."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])
        payload = {
            "sku": "SP-UI",
            "name": "UI Product",
            "description": "Dashboard",
            "category": str(product_category.id),
            "unit": "piece",
            "cost_price": "10,000",
            "selling_price": "12,000",
            "status": "active",
        }

        # Act
        created = client.post("/products/create/", payload)
        product = Product.objects.get(sku="SP-UI")
        updated = client.post(
            f"/products/{product.id}/update/",
            {**payload, "sku": product.sku, "name": "Updated UI"},
        )
        deleted = client.post(f"/products/{product.id}/delete/")
        restored = client.post(f"/products/{product.id}/restore/")

        # Assert
        assert created.status_code == 302
        assert updated.status_code == 302
        assert deleted.status_code == 302
        assert restored.status_code == 302
        assert Product.objects.get(id=product.id).name == "Updated UI"

    def test_category_pages_render_for_authorized_user(
        self,
        client: Client,
        user_with_product_role: User,
        user_data: dict[str, str],
        product_category: Category,
    ) -> None:
        """Test Category list/create forms render and search works."""
        # Arrange
        client.login(email=user_data["email"], password=user_data["password"])

        # Act
        listed = client.get("/categories/", {"search": "Beverages"})
        created = client.post(
            "/categories/create/",
            {"name": "Snacks", "description": "Food"},
        )

        # Assert
        assert listed.status_code == 200
        assert product_category.name in listed.content.decode()
        assert created.status_code == 302
        assert Category.objects.filter(name="Snacks").exists()


def test_product_validation_helpers() -> None:
    """Test SKU normalization and Decimal price parsing helpers."""
    # Arrange & Act
    sku = normalize_sku(" sp-01 ")
    valid_price = parse_price("1,250.50")
    invalid_price = parse_price("not-a-price")

    # Assert
    assert sku == "SP-01"
    assert valid_price == Decimal("1250.50")
    assert invalid_price is None
