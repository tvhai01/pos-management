"""
Shared pytest fixtures for the POS Management System.

Provides reusable fixtures for creating test users, API clients,
roles, permissions, and other common test dependencies.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.constants import PermissionAction, PermissionResource
from apps.accounts.models import Permission, Role, User, UserRole
from apps.customers.models import Customer
from apps.inventory.models import Inventory
from apps.inventory.services import InventoryService
from apps.product.models import Category, Product

# =============================================================================
# API Client Fixtures
# =============================================================================


@pytest.fixture
def api_client() -> APIClient:
    """Return an unauthenticated DRF API test client.

    Returns:
        An APIClient instance for making test API requests.
    """
    return APIClient()


# =============================================================================
# User Data Fixtures
# =============================================================================


@pytest.fixture
def user_data() -> dict[str, str]:
    """Return a valid user data dictionary for creating test users.

    Returns:
        A dict with email, full_name, phone, and password.
    """
    return {
        "email": "testuser@example.com",
        "full_name": "Test User",
        "phone": "0123456789",
        "password": "SecurePass123!",
    }


# =============================================================================
# User Fixtures
# =============================================================================


@pytest.fixture
def create_user(user_data: dict[str, str]) -> User:
    """Create and return a regular test user.

    Args:
        user_data: Dict with user fields from the user_data fixture.

    Returns:
        A persisted User instance.
    """
    return User.objects.create_user(
        email=user_data["email"],
        password=user_data["password"],
        full_name=user_data["full_name"],
        phone=user_data["phone"],
    )


@pytest.fixture
def create_superuser() -> User:
    """Create and return a test superuser.

    Returns:
        A persisted superuser User instance.
    """
    return User.objects.create_superuser(
        email="admin@example.com",
        password="AdminPass123!",
        full_name="Admin User",
    )


@pytest.fixture
def inactive_user() -> User:
    """Create and return an inactive test user.

    Returns:
        A persisted inactive User instance.
    """
    return User.objects.create_user(
        email="inactive@example.com",
        password="InactivePass123!",
        full_name="Inactive User",
        is_active=False,
    )


# =============================================================================
# Authenticated Client Fixtures
# =============================================================================


@pytest.fixture
def authenticated_client(
    api_client: APIClient,
    create_user: User,
) -> APIClient:
    """Return an authenticated API client.

    Args:
        api_client: An APIClient instance.
        create_user: A persisted User instance.

    Returns:
        An APIClient authenticated via force_authenticate.
    """
    api_client.force_authenticate(user=create_user)
    return api_client


@pytest.fixture
def superuser_client(
    api_client: APIClient,
    create_superuser: User,
) -> APIClient:
    """Return an API client authenticated as superuser.

    Args:
        api_client: An APIClient instance.
        create_superuser: A persisted superuser User instance.

    Returns:
        An APIClient authenticated as superuser.
    """
    api_client.force_authenticate(user=create_superuser)
    return api_client


@pytest.fixture
def user_tokens(create_user: User) -> dict[str, str]:
    """Generate JWT tokens for the test user.

    Args:
        create_user: A persisted User instance.

    Returns:
        A dict with 'access' and 'refresh' token strings.
    """
    refresh = RefreshToken.for_user(create_user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


@pytest.fixture
def superuser_tokens(create_superuser: User) -> dict[str, str]:
    """Generate JWT tokens for the superuser.

    Args:
        create_superuser: A persisted superuser User instance.

    Returns:
        A dict with 'access' and 'refresh' token strings.
    """
    refresh = RefreshToken.for_user(create_superuser)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


# =============================================================================
# RBAC Fixtures
# =============================================================================


@pytest.fixture
def view_role_permission() -> Permission:
    """Create a 'view role' permission.

    Returns:
        A persisted Permission instance.
    """
    return Permission.objects.create(
        name="View Role",
        action=PermissionAction.VIEW,
        resource=PermissionResource.ROLE,
    )


@pytest.fixture
def create_role_permission() -> Permission:
    """Create a 'create role' permission.

    Returns:
        A persisted Permission instance.
    """
    return Permission.objects.create(
        name="Create Role",
        action=PermissionAction.CREATE,
        resource=PermissionResource.ROLE,
    )


@pytest.fixture
def update_role_permission() -> Permission:
    """Create an 'update role' permission.

    Returns:
        A persisted Permission instance.
    """
    return Permission.objects.create(
        name="Update Role",
        action=PermissionAction.UPDATE,
        resource=PermissionResource.ROLE,
    )


@pytest.fixture
def delete_role_permission() -> Permission:
    """Create a 'delete role' permission.

    Returns:
        A persisted Permission instance.
    """
    return Permission.objects.create(
        name="Delete Role",
        action=PermissionAction.DELETE,
        resource=PermissionResource.ROLE,
    )


@pytest.fixture
def all_role_permissions(
    view_role_permission: Permission,
    create_role_permission: Permission,
    update_role_permission: Permission,
    delete_role_permission: Permission,
) -> list[Permission]:
    """Return all role-related permissions.

    Returns:
        A list of all Permission instances for the 'role' resource.
    """
    return [
        view_role_permission,
        create_role_permission,
        update_role_permission,
        delete_role_permission,
    ]


@pytest.fixture
def staff_role(all_role_permissions: list[Permission]) -> Role:
    """Create a Staff role with all role permissions.

    Returns:
        A persisted Role instance with permissions assigned.
    """
    role = Role.objects.create(
        name="Staff",
        description="Staff role for testing",
    )
    role.permissions.set(all_role_permissions)
    return role


@pytest.fixture
def user_with_role(
    create_user: User,
    staff_role: Role,
) -> User:
    """Create a user with the Staff role assigned.

    Args:
        create_user: A persisted User instance.
        staff_role: A persisted Role instance with permissions.

    Returns:
        The User instance with the Staff role assigned.
    """
    UserRole.objects.create(user=create_user, role=staff_role)
    return create_user


@pytest.fixture
def authenticated_staff_client(
    api_client: APIClient,
    user_with_role: User,
) -> APIClient:
    """Return an API client authenticated as a user with the Staff role.

    Args:
        api_client: An APIClient instance.
        user_with_role: A user with the Staff role assigned.

    Returns:
        An APIClient authenticated as the staff user.
    """
    api_client.force_authenticate(user=user_with_role)
    return api_client


# =============================================================================
# Customer Fixtures (Sprint 2)
# =============================================================================


@pytest.fixture
def customer_data() -> dict[str, str]:
    """Return a valid customer data dictionary for creating test customers.

    Returns:
        A dict with customer_code, full_name, phone, email, address.
    """
    return {
        "customer_code": "CUS000001",
        "full_name": "Nguyen Van A",
        "phone": "0901234567",
        "email": "customer@example.com",
        "address": "123 Le Loi, District 1, HCMC",
    }


@pytest.fixture
def create_customer(customer_data: dict[str, str]) -> Customer:
    """Create and return a persisted test customer.

    Args:
        customer_data: Dict with customer fields from the customer_data fixture.

    Returns:
        A persisted Customer instance.
    """
    return Customer.objects.create(**customer_data)


@pytest.fixture
def view_customer_permission() -> Permission:
    """Create a 'view customer' permission."""
    return Permission.objects.create(
        name="View Customer",
        action=PermissionAction.VIEW,
        resource=PermissionResource.CUSTOMER,
    )


@pytest.fixture
def create_customer_permission() -> Permission:
    """Create a 'create customer' permission."""
    return Permission.objects.create(
        name="Create Customer",
        action=PermissionAction.CREATE,
        resource=PermissionResource.CUSTOMER,
    )


@pytest.fixture
def update_customer_permission() -> Permission:
    """Create an 'update customer' permission."""
    return Permission.objects.create(
        name="Update Customer",
        action=PermissionAction.UPDATE,
        resource=PermissionResource.CUSTOMER,
    )


@pytest.fixture
def delete_customer_permission() -> Permission:
    """Create a 'delete customer' permission."""
    return Permission.objects.create(
        name="Delete Customer",
        action=PermissionAction.DELETE,
        resource=PermissionResource.CUSTOMER,
    )


@pytest.fixture
def export_customer_permission() -> Permission:
    """Create an 'export customer' permission."""
    return Permission.objects.create(
        name="Export Customer",
        action=PermissionAction.EXPORT,
        resource=PermissionResource.CUSTOMER,
    )


@pytest.fixture
def all_customer_permissions(
    view_customer_permission: Permission,
    create_customer_permission: Permission,
    update_customer_permission: Permission,
    delete_customer_permission: Permission,
    export_customer_permission: Permission,
) -> list[Permission]:
    """Return all customer-related permissions."""
    return [
        view_customer_permission,
        create_customer_permission,
        update_customer_permission,
        delete_customer_permission,
        export_customer_permission,
    ]


@pytest.fixture
def customer_manager_role(all_customer_permissions: list[Permission]) -> Role:
    """Create a Customer Manager role with all customer permissions.

    Returns:
        A persisted Role instance with permissions assigned.
    """
    role = Role.objects.create(
        name="Customer Manager",
        description="Full access to customer management for testing",
    )
    role.permissions.set(all_customer_permissions)
    return role


@pytest.fixture
def user_with_customer_role(
    create_user: User,
    customer_manager_role: Role,
) -> User:
    """Create a user with the Customer Manager role assigned.

    Returns:
        The User instance with the Customer Manager role assigned.
    """
    UserRole.objects.create(user=create_user, role=customer_manager_role)
    return create_user


@pytest.fixture
def authenticated_customer_client(
    api_client: APIClient,
    user_with_customer_role: User,
) -> APIClient:
    """Return an API client authenticated as a user with the Customer Manager role.

    Returns:
        An APIClient authenticated as the customer-manager user.
    """
    api_client.force_authenticate(user=user_with_customer_role)
    return api_client


# =============================================================================
# Product Fixtures
# =============================================================================


@pytest.fixture
def product_category() -> Category:
    """Create a live category for Product tests."""
    return Category.objects.create(name="Beverages", description="Drinks")


@pytest.fixture
def product_data(product_category: Category) -> dict:
    """Return valid Product creation data."""
    return {
        "sku": "SP001",
        "name": "Mineral Water",
        "description": "500 ml bottle",
        "category_id": product_category.id,
        "unit": "bottle",
        "cost_price": Decimal("5000.00"),
        "selling_price": Decimal("7000.00"),
        "status": "active",
    }


@pytest.fixture
def product(product_category: Category) -> Product:
    """Create a persisted live Product."""
    return Product.objects.create(
        sku="SP001",
        name="Mineral Water",
        description="500 ml bottle",
        category=product_category,
        unit="bottle",
        cost_price=Decimal("5000.00"),
        selling_price=Decimal("7000.00"),
        status="active",
    )


@pytest.fixture
def all_product_permissions() -> list[Permission]:
    """Create all Product and Category permissions used by tests."""
    definitions = [
        (PermissionAction.VIEW, PermissionResource.PRODUCT),
        (PermissionAction.CREATE, PermissionResource.PRODUCT),
        (PermissionAction.UPDATE, PermissionResource.PRODUCT),
        (PermissionAction.DELETE, PermissionResource.PRODUCT),
        (PermissionAction.VIEW, PermissionResource.CATEGORY),
        (PermissionAction.CREATE, PermissionResource.CATEGORY),
        (PermissionAction.UPDATE, PermissionResource.CATEGORY),
        (PermissionAction.DELETE, PermissionResource.CATEGORY),
    ]
    return [
        Permission.objects.create(
            name=f"{action.value.title()} {resource.value.title()}",
            action=action,
            resource=resource,
        )
        for action, resource in definitions
    ]


@pytest.fixture
def product_manager_role(all_product_permissions: list[Permission]) -> Role:
    """Create a role with full Product and Category management access."""
    role = Role.objects.create(name="Product Manager")
    role.permissions.set(all_product_permissions)
    return role


@pytest.fixture
def user_with_product_role(create_user: User, product_manager_role: Role) -> User:
    """Assign full Product permissions to the standard test user."""
    UserRole.objects.create(user=create_user, role=product_manager_role)
    return create_user


@pytest.fixture
def authenticated_product_client(
    api_client: APIClient, user_with_product_role: User
) -> APIClient:
    """Return an API client authenticated with Product permissions."""
    api_client.force_authenticate(user=user_with_product_role)
    return api_client


# =============================================================================
# Inventory Fixtures
# =============================================================================


@pytest.fixture
def inventory(product: Product) -> Inventory:
    """Create the zero-balance Inventory for the standard Product fixture."""
    return InventoryService.initialize_inventory(product)


@pytest.fixture
def all_inventory_permissions() -> list[Permission]:
    """Create view/create/update Inventory permissions."""
    definitions = (
        PermissionAction.VIEW,
        PermissionAction.CREATE,
        PermissionAction.UPDATE,
    )
    return [
        Permission.objects.create(
            name=f"{action.value.title()} Inventory",
            action=action,
            resource=PermissionResource.INVENTORY,
        )
        for action in definitions
    ]


@pytest.fixture
def inventory_manager_role(all_inventory_permissions: list[Permission]) -> Role:
    """Create a role with complete Inventory access."""
    role = Role.objects.create(name="Inventory Manager")
    role.permissions.set(all_inventory_permissions)
    return role


@pytest.fixture
def user_with_inventory_role(
    create_user: User,
    inventory_manager_role: Role,
) -> User:
    """Assign complete Inventory access to the standard user."""
    UserRole.objects.create(user=create_user, role=inventory_manager_role)
    return create_user


@pytest.fixture
def authenticated_inventory_client(
    api_client: APIClient,
    user_with_inventory_role: User,
) -> APIClient:
    """Return an API client authenticated with Inventory permissions."""
    api_client.force_authenticate(user=user_with_inventory_role)
    return api_client


# =============================================================================
# Report Fixtures
# =============================================================================


@pytest.fixture
def view_report_permission() -> Permission:
    """Create a 'view report' permission."""
    return Permission.objects.create(
        name="View Report",
        action=PermissionAction.VIEW,
        resource=PermissionResource.REPORT,
    )


@pytest.fixture
def export_report_permission() -> Permission:
    """Create an 'export report' permission."""
    return Permission.objects.create(
        name="Export Report",
        action=PermissionAction.EXPORT,
        resource=PermissionResource.REPORT,
    )


@pytest.fixture
def view_only_report_role(view_report_permission: Permission) -> Role:
    """Create a role with only `view:report` (no export)."""
    role = Role.objects.create(name="Report Viewer")
    role.permissions.set([view_report_permission])
    return role


@pytest.fixture
def report_manager_role(
    view_report_permission: Permission,
    export_report_permission: Permission,
) -> Role:
    """Create a role with full Report access (view + export)."""
    role = Role.objects.create(name="Report Manager")
    role.permissions.set([view_report_permission, export_report_permission])
    return role


@pytest.fixture
def user_with_view_only_report_role(create_user: User, view_only_report_role: Role) -> User:
    """Assign only `view:report` to the standard test user."""
    UserRole.objects.create(user=create_user, role=view_only_report_role)
    return create_user


@pytest.fixture
def user_with_report_role(create_user: User, report_manager_role: Role) -> User:
    """Assign full Report access to the standard test user."""
    UserRole.objects.create(user=create_user, role=report_manager_role)
    return create_user


@pytest.fixture
def authenticated_view_only_report_client(
    api_client: APIClient, user_with_view_only_report_role: User
) -> APIClient:
    """Return an API client authenticated with only `view:report`."""
    api_client.force_authenticate(user=user_with_view_only_report_role)
    return api_client


@pytest.fixture
def authenticated_report_client(
    api_client: APIClient, user_with_report_role: User
) -> APIClient:
    """Return an API client authenticated with full Report access."""
    api_client.force_authenticate(user=user_with_report_role)
    return api_client
