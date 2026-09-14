"""
Views for the Dashboard app.

Session-authenticated, server-rendered admin UI. Same layering rule as
the DRF API: views stay thin and delegate reads to Selectors, writes to
Services. The only new primitive here is `require_permission` (session
equivalent of DRF's `HasPermission`), plus Django's own `authenticate`/
`login`/`logout` for establishing the session (the session-auth analogue
of `AuthService.login` issuing JWTs).
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Any, cast
from uuid import UUID

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.accounts.constants import PermissionAction, PermissionResource
from apps.accounts.models import Permission, User
from apps.accounts.selectors import PermissionSelector, RoleSelector, UserSelector
from apps.accounts.services import RoleService, UserService
from apps.customers.constants import CustomerStatus
from apps.customers.exceptions import CustomerNotFoundError
from apps.customers.selectors import CustomerSelector
from apps.customers.services import CustomerService
from apps.dashboard.decorators import require_permission
from apps.dashboard.forms import (
    CategoryForm,
    CustomerForm,
    LoginForm,
    LowStockThresholdForm,
    ProductUIForm,
    ReportFilterForm,
    RoleForm,
    StaffForm,
    StockMovementForm,
)
from apps.inventory.constants import StockStatus
from apps.inventory.exceptions import (
    InsufficientStockError,
    InventoryProductNotFoundError,
    NoStockChangeError,
)
from apps.inventory.selectors import InventorySelector, StockMovementSelector
from apps.inventory.services import InventoryService
from apps.invoices.constants import InvoiceStatus
from apps.invoices.models import Invoice
from apps.invoices.selectors import InvoiceSelector
from apps.invoices.services import InvoiceService
from apps.orders.constants import OrderStatus
from apps.orders.selectors import OrderSelector
from apps.orders.services import OrderService
from apps.payments.models import Payment
from apps.payments.services import PaymentService
from apps.product.constants import ProductStatus
from apps.product.exceptions import (
    CategoryHasProductsError,
    CategoryNotFoundError,
    ProductNotFoundError,
)
from apps.product.selectors import CategorySelector, ProductSelector
from apps.product.services import CategoryService, ProductService
from apps.reports import exports as report_exports
from apps.reports.constants import ReportType
from apps.reports.selectors import ReportSelector
from apps.reports.services import ReportInsightService

logger = logging.getLogger(__name__)

# =============================================================================
# Auth
# =============================================================================


def _authenticated_user(request: HttpRequest) -> User:
    """Narrow request.user after login/permission decorators have run."""
    return cast(User, request.user)


def login_view(request: HttpRequest) -> HttpResponse:
    """Render the login form and authenticate on submit.

    GET  /login/
    POST /login/
    """
    if request.user.is_authenticated:
        return redirect("dashboard:index")

    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        # Django's ModelBackend already rejects is_active=False accounts
        # internally (returns None), so a wrong password and a deactivated
        # account are indistinguishable here — same as the JWT login flow
        # in AuthService, which also can't tell them apart for this reason.
        user = authenticate(
            request,
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
        )
        if user is None:
            form.add_error(None, "Email hoặc mật khẩu không đúng.")
        else:
            login(request, user)
            return redirect("dashboard:index")

    return render(request, "dashboard/login.html", {"form": form})


@login_required(login_url="dashboard:login")
def logout_view(request: HttpRequest) -> HttpResponse:
    """Log the current user out.

    POST /logout/
    """
    logout(request)
    return redirect("dashboard:login")


# =============================================================================
# Home
# =============================================================================


@login_required(login_url="dashboard:login")
def index(request: HttpRequest) -> HttpResponse:
    """Render the dashboard home — a directory of feature modules.

    Every module is listed; only ones the user holds `view:<resource>`
    for (or is superuser) render as a clickable link.

    GET /
    """
    modules: list[dict[str, Any]] = [
        {
            "name": "Khách hàng",
            "description": "Tạo, cập nhật, tìm kiếm, xoá mềm khách hàng.",
            "url_name": "dashboard:customer-list",
            "available": PermissionSelector.user_has_permission(
                _authenticated_user(request), "view", "customer"
            ),
        },
        {
            "name": "Sản phẩm",
            "description": "Quản lý sản phẩm, danh mục, giá và trạng thái kinh doanh.",
            "url_name": "dashboard:product-list",
            "available": PermissionSelector.user_has_permission(
                _authenticated_user(request), "view", "product"
            ),
        },
        {
            "name": "Kho hàng",
            "description": "Theo dõi tồn, nhập, xuất và điều chỉnh số lượng.",
            "url_name": "dashboard:inventory-list",
            "available": PermissionSelector.user_has_permission(
                _authenticated_user(request), "view", "inventory"
            ),
        },
        {
            "name": "Hóa đơn và thanh toán",
            "description": "Theo dõi hóa đơn, QR payment và lịch sử giao dịch.",
            "url_name": "dashboard:invoice-list",
            "available": PermissionSelector.user_has_permission(
                _authenticated_user(request), "view", "invoice"
            ),
        },
        {
            "name": "Đơn hàng",
            "description": "Chọn sản phẩm hiện có, tạo đơn và theo dõi thanh toán.",
            "url_name": "dashboard:order-list",
            "available": PermissionSelector.user_has_permission(
                _authenticated_user(request), "view", "order"
            ),
        },
        {
            "name": "Nhân viên",
            "description": "Tạo tài khoản nhân viên và gán vai trò (role).",
            "url_name": "dashboard:staff-list",
            "available": PermissionSelector.user_has_permission(
                _authenticated_user(request), "view", "user"
            ),
        },
        {
            "name": "Báo cáo",
            "description": "Doanh thu, sản phẩm bán chạy, tồn kho, thanh toán, "
            "khách hàng.",
            "url_name": "dashboard:report-dashboard",
            "available": PermissionSelector.user_has_permission(
                _authenticated_user(request), "view", "report"
            ),
        },
        {
            "name": "Django Admin",
            "description": "Trang quản trị dữ liệu trực tiếp (mọi model).",
            "url_name": None,
            "url": "/admin/",
            "available": request.user.is_staff,
        },
    ]
    return render(request, "dashboard/index.html", {"modules": modules})


# =============================================================================
# Customers
# =============================================================================


@require_permission("view", "customer")
def customer_list(request: HttpRequest) -> HttpResponse:
    """List/search/filter customers with pagination.

    GET /customers/?search=&status=&page=
    """
    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()

    queryset = CustomerSelector.search_customers(search=search, status=status)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "dashboard/customers/list.html",
        {
            "page_obj": page_obj,
            "search": search,
            "status": status,
            "status_choices": CustomerStatus.choices,
            "can_create": PermissionSelector.user_has_permission(
                _authenticated_user(request), "create", "customer"
            ),
            "can_update": PermissionSelector.user_has_permission(
                _authenticated_user(request), "update", "customer"
            ),
            "can_delete": PermissionSelector.user_has_permission(
                _authenticated_user(request), "delete", "customer"
            ),
        },
    )


@require_permission("create", "customer")
def customer_create(request: HttpRequest) -> HttpResponse:
    """Create a new customer.

    GET  /customers/create/
    POST /customers/create/
    """
    form = CustomerForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        CustomerService.create_customer(
            **form.cleaned_data, created_by=_authenticated_user(request)
        )
        messages.success(request, "Đã tạo khách hàng thành công.")
        return redirect("dashboard:customer-list")

    return render(
        request,
        "dashboard/customers/form.html",
        {"form": form, "is_edit": False},
    )


@require_permission("update", "customer")
def customer_edit(request: HttpRequest, customer_id: UUID) -> HttpResponse:
    """Update an existing customer.

    GET  /customers/{id}/edit/
    POST /customers/{id}/edit/
    """
    customer = CustomerSelector.get_customer_by_id(customer_id)
    if customer is None:
        messages.error(request, "Không tìm thấy khách hàng.")
        return redirect("dashboard:customer-list")

    if request.method == "POST":
        form = CustomerForm(request.POST, customer_id=customer_id)
        if form.is_valid():
            CustomerService.update_customer(
                customer_id=customer_id,
                updated_by=_authenticated_user(request),
                **form.cleaned_data,
            )
            messages.success(request, "Đã cập nhật khách hàng thành công.")
            return redirect("dashboard:customer-list")
    else:
        form = CustomerForm(
            customer_id=customer_id,
            initial={
                "customer_code": customer.customer_code,
                "full_name": customer.full_name,
                "phone": customer.phone,
                "email": customer.email,
                "gender": customer.gender,
                "birthday": customer.birthday,
                "address": customer.address,
                "note": customer.note,
                "status": customer.status,
            },
        )

    return render(
        request,
        "dashboard/customers/form.html",
        {"form": form, "is_edit": True, "customer": customer},
    )


@require_permission("delete", "customer")
def customer_delete(request: HttpRequest, customer_id: UUID) -> HttpResponse:
    """Confirm and soft-delete a customer.

    GET  /customers/{id}/delete/   — confirmation page
    POST /customers/{id}/delete/   — performs the soft delete
    """
    customer = CustomerSelector.get_customer_by_id(customer_id)
    if customer is None:
        messages.error(request, "Không tìm thấy khách hàng.")
        return redirect("dashboard:customer-list")

    if request.method == "POST":
        try:
            CustomerService.delete_customer(
                customer_id=customer_id, deleted_by=_authenticated_user(request)
            )
            messages.success(request, "Đã xoá khách hàng.")
        except CustomerNotFoundError:
            messages.error(request, "Không tìm thấy khách hàng.")
        return redirect("dashboard:customer-list")

    return render(
        request, "dashboard/customers/confirm_delete.html", {"customer": customer}
    )


# =============================================================================
# Staff (User Management)
# =============================================================================


@require_permission("view", "user")
def staff_list(request: HttpRequest) -> HttpResponse:
    """List/search staff users with pagination.

    GET /staff/?search=&is_active=&page=
    """
    search = request.GET.get("search", "").strip()
    is_active = request.GET.get("is_active", "").strip()

    queryset = UserSelector.search_users(search=search, is_active=is_active)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "dashboard/staff/list.html",
        {
            "page_obj": page_obj,
            "search": search,
            "is_active": is_active,
            "can_create": PermissionSelector.user_has_permission(
                _authenticated_user(request), "create", "user"
            ),
            "can_update": PermissionSelector.user_has_permission(
                _authenticated_user(request), "update", "user"
            ),
            "can_delete": PermissionSelector.user_has_permission(
                _authenticated_user(request), "delete", "user"
            ),
        },
    )


@require_permission("create", "user")
def staff_create(request: HttpRequest) -> HttpResponse:
    """Create a new staff user.

    GET  /staff/create/
    POST /staff/create/
    """
    form = StaffForm(request.POST or None, is_edit=False)

    if request.method == "POST" and form.is_valid():
        UserService.create_user(
            email=form.cleaned_data["email"],
            full_name=form.cleaned_data["full_name"],
            password=form.cleaned_data["password"],
            phone=form.cleaned_data["phone"],
            role_ids=[role.id for role in form.cleaned_data["roles"]],
            created_by=_authenticated_user(request),
        )
        messages.success(request, "Đã tạo nhân viên thành công.")
        return redirect("dashboard:staff-list")

    return render(
        request,
        "dashboard/staff/form.html",
        {"form": form, "is_edit": False},
    )


@require_permission("update", "user")
def staff_edit(request: HttpRequest, user_id: UUID) -> HttpResponse:
    """Update an existing staff user.

    GET  /staff/{id}/edit/
    POST /staff/{id}/edit/
    """
    staff_user = UserSelector.get_user_by_id(user_id)
    if staff_user is None:
        messages.error(request, "Không tìm thấy nhân viên.")
        return redirect("dashboard:staff-list")

    if request.method == "POST":
        form = StaffForm(request.POST, user_id=user_id, is_edit=True)
        if form.is_valid():
            UserService.update_user(
                user_id=user_id,
                full_name=form.cleaned_data["full_name"],
                phone=form.cleaned_data["phone"],
                is_active=form.cleaned_data["is_active"],
                role_ids=[role.id for role in form.cleaned_data["roles"]],
            )
            if form.cleaned_data["password"]:
                staff_user.set_password(form.cleaned_data["password"])
                staff_user.save(update_fields=["password"])
            messages.success(request, "Đã cập nhật nhân viên thành công.")
            return redirect("dashboard:staff-list")
    else:
        form = StaffForm(
            user_id=user_id,
            is_edit=True,
            initial={
                "email": staff_user.email,
                "full_name": staff_user.full_name,
                "phone": staff_user.phone,
                "is_active": staff_user.is_active,
                "roles": staff_user.roles.values_list("id", flat=True),
            },
        )

    return render(
        request,
        "dashboard/staff/form.html",
        {"form": form, "is_edit": True, "staff_user": staff_user},
    )


@require_POST
@require_permission("delete", "user")
def staff_deactivate(request: HttpRequest, user_id: UUID) -> HttpResponse:
    """Deactivate a staff user (reversible, not a hard delete).

    POST /staff/{id}/deactivate/
    """
    UserService.deactivate_user(user_id=user_id)
    messages.success(request, "Đã vô hiệu hoá nhân viên.")
    return redirect("dashboard:staff-list")


@require_POST
@require_permission("update", "user")
def staff_activate(request: HttpRequest, user_id: UUID) -> HttpResponse:
    """Reactivate a previously deactivated staff user.

    POST /staff/{id}/activate/
    """
    UserService.activate_user(user_id=user_id)
    messages.success(request, "Đã kích hoạt lại nhân viên.")
    return redirect("dashboard:staff-list")


# =============================================================================
# Roles
# =============================================================================

# Fixed column order for the permission matrix (View/Create/Update/Delete).
# Any other action a resource happens to have (Export, Approve, ...) still
# renders — as an extra checkbox per row — so saving a role never silently
# drops a permission that isn't one of these four.
_PERMISSION_MATRIX_COLUMNS: tuple[str, ...] = (
    PermissionAction.VIEW,
    PermissionAction.CREATE,
    PermissionAction.UPDATE,
    PermissionAction.DELETE,
)


def _build_permission_matrix(checked_ids: set[str]) -> list[dict[str, Any]]:
    """Group all permissions by resource (module) for a checkbox matrix.

    Args:
        checked_ids: Permission UUIDs (as strings) that should render checked.

    Returns:
        One row per resource that has at least one permission: the resource
        label, a fixed-order cell per column in `_PERMISSION_MATRIX_COLUMNS`
        (`None` if that resource has no such permission), and any remaining
        permissions for that resource under "extra".
    """
    permissions_by_resource: dict[str, dict[str, Permission]] = {}
    for permission in RoleSelector.get_all_permissions():
        permissions_by_resource.setdefault(permission.resource, {})[
            permission.action
        ] = permission

    def _cell(permission: Permission | None) -> dict[str, Any] | None:
        if permission is None:
            return None
        return {
            "permission": permission,
            "checked": str(permission.id) in checked_ids,
        }

    matrix: list[dict[str, Any]] = []
    for resource_value, resource_label in PermissionResource.choices:
        actions = permissions_by_resource.get(resource_value)
        if not actions:
            continue
        matrix.append(
            {
                "resource_label": resource_label,
                "cells": [
                    _cell(actions.get(action)) for action in _PERMISSION_MATRIX_COLUMNS
                ],
                "extra": [
                    _cell(permission)
                    for action, permission in actions.items()
                    if action not in _PERMISSION_MATRIX_COLUMNS
                ],
            }
        )
    return matrix


@require_permission("view", "role")
def role_list(request: HttpRequest) -> HttpResponse:
    """List all roles with their permission/user counts.

    GET /staff/roles/
    """
    roles = RoleSelector.get_all_roles()

    return render(
        request,
        "dashboard/roles/list.html",
        {
            "roles": roles,
            "can_create": PermissionSelector.user_has_permission(
                _authenticated_user(request), "create", "role"
            ),
            "can_update": PermissionSelector.user_has_permission(
                _authenticated_user(request), "update", "role"
            ),
        },
    )


@require_permission("create", "role")
def role_create(request: HttpRequest) -> HttpResponse:
    """Create a new role with optional permission assignment.

    GET  /staff/roles/create/
    POST /staff/roles/create/
    """
    form = RoleForm(request.POST or None)
    checked_ids = set(request.POST.getlist("permissions")) if request.POST else set()

    if request.method == "POST" and form.is_valid():
        RoleService.create_role(
            name=form.cleaned_data["name"],
            description=form.cleaned_data["description"],
            permission_ids=[p.id for p in form.cleaned_data["permissions"]],
        )
        messages.success(request, "Đã tạo vai trò thành công.")
        return redirect("dashboard:role-list")

    return render(
        request,
        "dashboard/roles/form.html",
        {
            "form": form,
            "is_edit": False,
            "permission_matrix": _build_permission_matrix(checked_ids),
        },
    )


@require_permission("update", "role")
def role_edit(request: HttpRequest, role_id: UUID) -> HttpResponse:
    """Update an existing role's name, description, and permissions.

    GET  /staff/roles/{id}/edit/
    POST /staff/roles/{id}/edit/
    """
    role = RoleSelector.get_role_by_id(role_id)
    if role is None:
        messages.error(request, "Không tìm thấy vai trò.")
        return redirect("dashboard:role-list")

    if request.method == "POST":
        form = RoleForm(request.POST, role_id=role_id)
        checked_ids = set(request.POST.getlist("permissions"))
        if form.is_valid():
            RoleService.update_role(
                role_id=role_id,
                name=form.cleaned_data["name"],
                description=form.cleaned_data["description"],
                permission_ids=[p.id for p in form.cleaned_data["permissions"]],
            )
            messages.success(request, "Đã cập nhật vai trò thành công.")
            return redirect("dashboard:role-list")
    else:
        checked_ids = {
            str(pid) for pid in role.permissions.values_list("id", flat=True)
        }
        form = RoleForm(
            role_id=role_id,
            initial={
                "name": role.name,
                "description": role.description,
                "permissions": role.permissions.values_list("id", flat=True),
            },
        )

    return render(
        request,
        "dashboard/roles/form.html",
        {
            "form": form,
            "is_edit": True,
            "role": role,
            "permission_matrix": _build_permission_matrix(checked_ids),
        },
    )


# =============================================================================
# Products / Categories
# =============================================================================


def _dashboard_page_size(value: str, total_count: int) -> int:
    """Return a bounded page size accepted by Product dashboard lists."""
    if value == "all":
        return max(total_count, 1)
    try:
        size = int(value)
    except (TypeError, ValueError):
        return 20
    return size if size in {5, 10, 20, 50} else 20


@require_permission("view", "product")
def product_list(request: HttpRequest) -> HttpResponse:
    """List/search/filter live products with pagination."""
    search = request.GET.get("search", "").strip()
    category_id = request.GET.get("category", "").strip()
    status_value = request.GET.get("status", "").strip()
    sort = request.GET.get("sort", "").strip()
    queryset = ProductSelector.search_products(
        search=search,
        category_id=category_id,
        status=status_value,
        sort=sort,
    )
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    page_products = list(page_obj.object_list)
    page_obj.object_list = page_products
    selected_id = request.GET.get("selected", "").strip()
    selected_product = next(
        (product for product in page_products if str(product.id) == selected_id),
        page_products[0] if page_products else None,
    )
    user = _authenticated_user(request)
    return render(
        request,
        "dashboard/products/products/list.html",
        {
            "products": page_obj,
            "categories": CategorySelector.get_all_categories(),
            "status_choices": ProductStatus.choices,
            "search": search,
            "selected_category": category_id,
            "status": status_value,
            "sort": sort,
            "selected_product": selected_product,
            "active_module": "product",
            "can_view_product": True,
            "can_view_inventory": PermissionSelector.user_has_permission(
                user, "view", "inventory"
            ),
            "can_view_report": PermissionSelector.user_has_permission(
                user, "view", "report"
            ),
            "can_create": PermissionSelector.user_has_permission(
                user, "create", "product"
            ),
            "can_update": PermissionSelector.user_has_permission(
                user, "update", "product"
            ),
            "can_delete": PermissionSelector.user_has_permission(
                user, "delete", "product"
            ),
        },
    )


@require_permission("create", "product")
def product_create(request: HttpRequest) -> HttpResponse:
    """Create a Product through ProductService."""
    form = ProductUIForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        payload = form.cleaned_data.copy()
        category = payload.pop("category", None)
        ProductService.create_product(
            **payload,
            category_id=category.id if category else None,
            created_by=_authenticated_user(request),
        )
        messages.success(request, "Đã tạo sản phẩm thành công.")
        return redirect("dashboard:product-list")
    return render(
        request,
        "dashboard/products/products/create.html",
        {"form": form, "title": "Thêm sản phẩm"},
    )


@require_permission("update", "product")
def product_update(request: HttpRequest, product_id: UUID) -> HttpResponse:
    """Update mutable Product fields through ProductService."""
    product = ProductSelector.get_product_by_id(product_id)
    if product is None:
        messages.error(request, "Không tìm thấy sản phẩm.")
        return redirect("dashboard:product-list")
    form = ProductUIForm(
        request.POST or None,
        request.FILES or None,
        instance=product,
    )
    if request.method == "POST" and form.is_valid():
        payload = form.cleaned_data.copy()
        payload.pop("sku", None)
        category = payload.pop("category", None)
        ProductService.update_product(
            product_id=product.id,
            category_id=category.id if category else None,
            updated_by=_authenticated_user(request),
            **payload,
        )
        messages.success(request, "Đã cập nhật sản phẩm thành công.")
        return redirect("dashboard:product-list")
    return render(
        request,
        "dashboard/products/products/create.html",
        {"form": form, "title": "Sửa sản phẩm", "product": product},
    )


@require_POST
@require_permission("delete", "product")
def product_delete(request: HttpRequest, product_id: UUID) -> HttpResponse:
    """Soft-delete a Product through ProductService."""
    try:
        ProductService.delete_product(
            product_id, deleted_by=_authenticated_user(request)
        )
        messages.success(request, "Đã chuyển sản phẩm vào thùng rác.")
    except ProductNotFoundError:
        messages.error(request, "Không tìm thấy sản phẩm.")
    return redirect("dashboard:product-list")


@require_POST
@require_permission("update", "product")
def product_restore(request: HttpRequest, product_id: UUID) -> HttpResponse:
    """Restore a soft-deleted Product through ProductService."""
    try:
        ProductService.restore_product(
            product_id, restored_by=_authenticated_user(request)
        )
        messages.success(request, "Đã khôi phục sản phẩm.")
    except ProductNotFoundError:
        messages.error(request, "Không tìm thấy sản phẩm đã xóa.")
    except CategoryNotFoundError:
        messages.error(request, "Hãy khôi phục danh mục của sản phẩm trước.")
    return redirect("dashboard:trash")


@require_permission("view", "category")
def category_list(request: HttpRequest) -> HttpResponse:
    """List/search/filter live categories with pagination."""
    search = request.GET.get("search", "").strip()
    has_products = request.GET.get("has_products", "").strip()
    sort = request.GET.get("sort", "").strip()
    per_page = request.GET.get("per_page", "20").strip()
    queryset = CategorySelector.search_categories(search, has_products, sort)
    paginator = Paginator(
        queryset,
        _dashboard_page_size(per_page, queryset.count()),
    )
    return render(
        request,
        "dashboard/products/categories/list.html",
        {
            "categories": paginator.get_page(request.GET.get("page")),
            "search": search,
            "has_products": has_products,
            "sort": sort,
            "per_page": per_page,
            "can_create": PermissionSelector.user_has_permission(
                _authenticated_user(request), "create", "category"
            ),
            "can_update": PermissionSelector.user_has_permission(
                _authenticated_user(request), "update", "category"
            ),
            "can_delete": PermissionSelector.user_has_permission(
                _authenticated_user(request), "delete", "category"
            ),
        },
    )


@require_permission("create", "category")
def category_create(request: HttpRequest) -> HttpResponse:
    """Create a Category through CategoryService."""
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        CategoryService.create_category(
            **form.cleaned_data,
            created_by=_authenticated_user(request),
        )
        messages.success(request, "Đã tạo danh mục thành công.")
        return redirect("dashboard:category-list")
    return render(
        request,
        "dashboard/products/categories/form.html",
        {"form": form, "title": "Thêm danh mục"},
    )


@require_permission("update", "category")
def category_update(request: HttpRequest, category_id: UUID) -> HttpResponse:
    """Update a Category through CategoryService."""
    category = CategorySelector.get_category_by_id(category_id)
    if category is None:
        messages.error(request, "Không tìm thấy danh mục.")
        return redirect("dashboard:category-list")
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        CategoryService.update_category(
            category_id=category.id,
            updated_by=_authenticated_user(request),
            **form.cleaned_data,
        )
        messages.success(request, "Đã cập nhật danh mục thành công.")
        return redirect("dashboard:category-list")
    return render(
        request,
        "dashboard/products/categories/form.html",
        {"form": form, "title": "Sửa danh mục", "category": category},
    )


@require_POST
@require_permission("delete", "category")
def category_delete(request: HttpRequest, category_id: UUID) -> HttpResponse:
    """Soft-delete an empty Category through CategoryService."""
    try:
        CategoryService.delete_category(
            category_id, deleted_by=_authenticated_user(request)
        )
        messages.success(request, "Đã chuyển danh mục vào thùng rác.")
    except CategoryHasProductsError:
        messages.error(request, "Không thể xóa danh mục đang chứa sản phẩm.")
    except CategoryNotFoundError:
        messages.error(request, "Không tìm thấy danh mục.")
    return redirect("dashboard:category-list")


@require_POST
@require_permission("update", "category")
def category_restore(request: HttpRequest, category_id: UUID) -> HttpResponse:
    """Restore a soft-deleted Category through CategoryService."""
    try:
        CategoryService.restore_category(
            category_id, restored_by=_authenticated_user(request)
        )
        messages.success(request, "Đã khôi phục danh mục.")
    except CategoryNotFoundError:
        messages.error(request, "Không tìm thấy danh mục đã xóa.")
    return redirect("dashboard:trash")


@require_permission("view", "product")
def trash(request: HttpRequest) -> HttpResponse:
    """Show soft-deleted Product and Category records for restoration."""
    return render(
        request,
        "dashboard/products/trash/trash.html",
        {
            "products": ProductSelector.get_deleted_products(),
            "categories": CategorySelector.get_deleted_categories(),
            "can_restore_product": PermissionSelector.user_has_permission(
                _authenticated_user(request), "update", "product"
            ),
            "can_restore_category": PermissionSelector.user_has_permission(
                _authenticated_user(request), "update", "category"
            ),
        },
    )


# =============================================================================
# Inventory
# =============================================================================


@require_permission("view", "inventory")
def inventory_list(request: HttpRequest) -> HttpResponse:
    """List/search/filter Product stock balances."""
    search = request.GET.get("search", "").strip()
    category_id = request.GET.get("category", "").strip()
    product_status = request.GET.get("product_status", "").strip()
    stock_status = request.GET.get("stock_status", "").strip()
    queryset = InventorySelector.search_inventories(
        search=search,
        category_id=category_id,
        product_status=product_status,
        stock_status=stock_status,
    )
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    page_inventories = list(page_obj.object_list)
    page_obj.object_list = page_inventories
    selected_id = request.GET.get("selected", "").strip()
    selected_inventory = next(
        (
            inventory
            for inventory in page_inventories
            if str(inventory.product_id) == selected_id
        ),
        page_inventories[0] if page_inventories else None,
    )
    recent_movements = (
        StockMovementSelector.get_product_movements(selected_inventory.product_id)[:5]
        if selected_inventory is not None
        else []
    )
    user = _authenticated_user(request)
    return render(
        request,
        "dashboard/inventory/list.html",
        {
            "inventories": page_obj,
            "categories": CategorySelector.get_all_categories(),
            "product_status_choices": ProductStatus.choices,
            "stock_status_choices": StockStatus.choices,
            "search": search,
            "selected_category": category_id,
            "product_status": product_status,
            "stock_status": stock_status,
            "selected_inventory": selected_inventory,
            "recent_movements": recent_movements,
            "active_module": "inventory",
            "can_view_product": PermissionSelector.user_has_permission(
                user, "view", "product"
            ),
            "can_view_inventory": True,
            "can_view_report": PermissionSelector.user_has_permission(
                user, "view", "report"
            ),
            "can_create_movement": PermissionSelector.user_has_permission(
                user, "create", "inventory"
            ),
        },
    )


@require_permission("view", "inventory")
def inventory_detail(request: HttpRequest, product_id: UUID) -> HttpResponse:
    """Show one current balance and its immutable movement history."""
    inventory = InventorySelector.get_inventory_by_product_id(product_id)
    if inventory is None:
        messages.error(request, "Không tìm thấy tồn kho của sản phẩm.")
        return redirect("dashboard:inventory-list")
    movements = StockMovementSelector.get_product_movements(product_id)
    paginator = Paginator(movements, 10)
    return render(
        request,
        "dashboard/inventory/detail.html",
        {
            "inventory": inventory,
            "movements": paginator.get_page(request.GET.get("page")),
            "movement_form": StockMovementForm(),
            "threshold_form": LowStockThresholdForm(
                initial={
                    "low_stock_threshold": format(
                        inventory.low_stock_threshold.normalize(), "f"
                    )
                }
            ),
            "can_create_movement": PermissionSelector.user_has_permission(
                _authenticated_user(request), "create", "inventory"
            ),
            "can_update_threshold": PermissionSelector.user_has_permission(
                _authenticated_user(request), "update", "inventory"
            ),
            "active_module": "inventory",
            "can_view_product": PermissionSelector.user_has_permission(
                _authenticated_user(request), "view", "product"
            ),
            "can_view_inventory": True,
            "can_view_report": PermissionSelector.user_has_permission(
                _authenticated_user(request), "view", "report"
            ),
        },
    )


@require_POST
@require_permission("create", "inventory")
def inventory_movement(request: HttpRequest, product_id: UUID) -> HttpResponse:
    """Record an inbound, outbound or adjustment movement."""
    form = StockMovementForm(request.POST)
    if form.is_valid():
        try:
            InventoryService.record_movement(
                product_id=product_id,
                created_by=_authenticated_user(request),
                **form.cleaned_data,
            )
            messages.success(request, "Đã ghi nhận giao dịch kho.")
        except InsufficientStockError:
            messages.error(request, "Không đủ số lượng tồn để xuất kho.")
        except NoStockChangeError:
            messages.error(request, "Số tồn điều chỉnh không thay đổi.")
        except InventoryProductNotFoundError:
            messages.error(request, "Sản phẩm không tồn tại hoặc đã bị xóa.")
    else:
        messages.error(request, "Dữ liệu giao dịch kho không hợp lệ.")
    return redirect("dashboard:inventory-detail", product_id=product_id)


@require_POST
@require_permission("update", "inventory")
def inventory_threshold(request: HttpRequest, product_id: UUID) -> HttpResponse:
    """Update one Product's low-stock warning threshold."""
    form = LowStockThresholdForm(request.POST)
    if form.is_valid():
        try:
            InventoryService.update_low_stock_threshold(
                product_id=product_id,
                threshold=form.cleaned_data["low_stock_threshold"],
                updated_by=_authenticated_user(request),
            )
            messages.success(request, "Đã cập nhật ngưỡng tồn thấp.")
        except InventoryProductNotFoundError:
            messages.error(request, "Sản phẩm không tồn tại hoặc đã bị xóa.")
    else:
        messages.error(request, "Ngưỡng tồn thấp không hợp lệ.")
    return redirect("dashboard:inventory-detail", product_id=product_id)


# =============================================================================
# Invoices and payments
# =============================================================================


@require_permission("view", "order")
def order_list(request: HttpRequest) -> HttpResponse:
    orders = OrderSelector.get_all()
    return render(
        request,
        "dashboard/orders/list.html",
        {
            "orders": orders,
            "can_create": PermissionSelector.user_has_permission(
                _authenticated_user(request), "create", "order"
            ),
        },
    )


@require_permission("create", "order")
def order_create(request: HttpRequest) -> HttpResponse:
    customers = CustomerSelector.get_all_customers()
    products = ProductSelector.get_all_products().filter(status="active")
    if request.method == "POST":
        try:
            customer_id = request.POST.get("customer_id", "").strip()
            customer = CustomerSelector.get_customer_by_id(customer_id)
            product_ids = request.POST.getlist("product_id")
            quantities = request.POST.getlist("quantity")
            payment_method = (request.POST.get("payment_method") or "MOMO").upper()
            if customer is None:
                raise ValueError("Vui lòng chọn khách hàng hợp lệ.")
            if not product_ids or len(product_ids) != len(quantities):
                raise ValueError("Vui lòng chọn ít nhất một sản phẩm.")
            if payment_method not in {"MOMO", "SEPAY", "PAYPAL", "MANUAL"}:
                raise ValueError("Phương thức thanh toán không hợp lệ.")
            order_items = []
            for product_id, quantity in zip(product_ids, quantities, strict=True):
                try:
                    normalized_quantity = int(quantity)
                except (TypeError, ValueError) as exc:
                    raise ValueError("Số lượng sản phẩm phải là số nguyên.") from exc
                if normalized_quantity < 1:
                    raise ValueError("Số lượng sản phẩm phải lớn hơn 0.")
                order_items.append({"product_id": product_id, "quantity": normalized_quantity})
            order, invoice = OrderService.create_order(
                customer=customer,
                items=order_items,
                created_by=_authenticated_user(request),
            )
            if payment_method == "MANUAL":
                PaymentService.create_manual_payment(
                    invoice.id,
                    amount=invoice.total_amount,
                    reference=f"AUTO-{invoice.invoice_number}",
                    note="Thanh toán tại quầy",
                    created_by=_authenticated_user(request),
                )
                messages.success(request, f"Đã tạo đơn {order.order_number} và ghi nhận thanh toán thủ công.")
                return redirect("dashboard:invoice-detail", invoice_id=invoice.id)
            if payment_method == "PAYPAL":
                InvoiceService.transition(invoice.id, InvoiceStatus.PENDING_PAYMENT, _authenticated_user(request))
                payment, checkout = PaymentService.create_paypal_payment(
                    invoice.id,
                    created_by=_authenticated_user(request),
                    return_url=request.build_absolute_uri(reverse("dashboard:invoice-return", kwargs={"invoice_id": invoice.id})),
                    cancel_url=request.build_absolute_uri(reverse("dashboard:invoice-return", kwargs={"invoice_id": invoice.id})),
                )
                messages.success(request, f"Đã tạo đơn {order.order_number} và chuyển sang thanh toán PayPal.")
                return render(
                    request,
                    "dashboard/invoices/checkout.html",
                    {"checkout": checkout, "invoice": invoice, "payment": payment},
                )
            if payment_method == "SEPAY":
                InvoiceService.transition(invoice.id, InvoiceStatus.PENDING_PAYMENT, _authenticated_user(request))
                return_url = request.build_absolute_uri(reverse("dashboard:invoice-return", kwargs={"invoice_id": invoice.id}))
                payment, checkout = PaymentService.create_sepay_payment(
                    invoice.id,
                    created_by=_authenticated_user(request),
                    return_url=return_url,
                )
                messages.success(request, f"Đã tạo đơn {order.order_number} và chuyển sang thanh toán SePay.")
                return render(
                    request,
                    "dashboard/invoices/checkout.html",
                    {"checkout": checkout, "invoice": invoice, "payment": payment},
                )
            InvoiceService.transition(invoice.id, InvoiceStatus.PENDING_PAYMENT, _authenticated_user(request))
            messages.success(request, f"Đã tạo đơn {order.order_number} và chuyển sang thanh toán MoMo.")
            return redirect("dashboard:invoice-qr", invoice_id=invoice.id)
        except (KeyError, ValueError) as exc:
            logger.warning("dashboard.order_create_validation_failed error=%s", exc)
            messages.error(request, str(exc) or "Dữ liệu đơn hàng không hợp lệ.")
    return render(
        request,
        "dashboard/orders/form.html",
        {"customers": customers, "products": products},
    )


@require_permission("view", "order")
def order_detail(request: HttpRequest, order_id: UUID) -> HttpResponse:
    order = OrderSelector.get_by_id(order_id)
    if order is None:
        messages.error(request, "Không tìm thấy đơn hàng.")
        return redirect("dashboard:order-list")
    invoice = getattr(order, "invoice", None)
    payments = invoice.payments.all().order_by("-created_at") if invoice else []
    transactions = invoice.transactions.all().order_by("-created_at") if invoice else []
    return render(
        request,
        "dashboard/orders/detail.html",
        {
            "order": order,
            "invoice": invoice,
            "payments": payments,
            "transactions": transactions,
            "can_update": PermissionSelector.user_has_permission(
                _authenticated_user(request), "update", "order"
            ),
            "order_statuses": OrderStatus.choices,
        },
    )


@require_permission("view", "invoice")
def invoice_list(request: HttpRequest) -> HttpResponse:
    """List invoices for the payment workflow."""
    invoices = InvoiceSelector.get_all()
    search = request.GET.get("search", "").strip()
    if search:
        invoices = invoices.filter(invoice_number__icontains=search)
    return render(
        request,
        "dashboard/invoices/list.html",
        {"invoices": invoices, "search": search},
    )


@require_permission("view", "invoice")
def invoice_detail(request: HttpRequest, invoice_id: UUID) -> HttpResponse:
    """Show invoice totals plus payment transaction history."""
    invoice = InvoiceSelector.get_by_id(invoice_id)
    if invoice is None:
        messages.error(request, "Không tìm thấy hóa đơn.")
        return redirect("dashboard:invoice-list")
    payments = invoice.payments.all().order_by("-created_at")
    transactions = invoice.transactions.all().order_by("-created_at")
    paid_amount = sum(
        (payment.amount for payment in payments if payment.status == "SUCCESS"),
        Decimal("0"),
    )
    return render(
        request,
        "dashboard/invoices/detail.html",
        {
            "invoice": invoice,
            "payments": payments,
            "transactions": transactions,
            "paid_amount": paid_amount,
            "remaining_amount": max(invoice.total_amount - paid_amount, Decimal("0")),
        },
    )


@require_POST
@require_permission("update", "invoice")
def invoice_pending(request: HttpRequest, invoice_id: UUID) -> HttpResponse:
    try:
        InvoiceService.transition(
            invoice_id, InvoiceStatus.PENDING_PAYMENT, _authenticated_user(request)
        )
        messages.success(request, "Hóa đơn đã chuyển sang chờ thanh toán.")
    except (Invoice.DoesNotExist, ValueError):
        messages.error(request, "Không thể chuyển trạng thái hóa đơn.")
    return redirect("dashboard:invoice-detail", invoice_id=invoice_id)


@require_permission("create", "payment")
def invoice_qr(request: HttpRequest, invoice_id: UUID) -> HttpResponse:
    try:
        invoice = InvoiceSelector.get_by_id(invoice_id)
        if invoice is None:
            raise Invoice.DoesNotExist
        return_url = request.build_absolute_uri(
            reverse("dashboard:invoice-return", kwargs={"invoice_id": invoice_id})
        )
        _, checkout = PaymentService.create_qr_payment(
            invoice_id,
            created_by=_authenticated_user(request),
            return_url=return_url,
        )
        return render(
            request,
            "dashboard/invoices/checkout.html",
            {"checkout": checkout, "invoice": invoice},
        )
    except (Invoice.DoesNotExist, ValueError) as exc:
        messages.error(request, f"Không thể tạo thanh toán QR: {exc}")
    except Exception:
        logger.exception("dashboard.invoice_qr_failed invoice=%s", invoice_id)
        messages.error(request, "Không thể tạo thanh toán QR. Vui lòng thử lại.")
    return redirect("dashboard:invoice-detail", invoice_id=invoice_id)


@require_permission("view", "invoice")
def invoice_return(request: HttpRequest, invoice_id: UUID) -> HttpResponse:
    """Sync invoice state after returning from a payment provider and send user back to the order."""
    try:
        invoice = InvoiceSelector.get_by_id(invoice_id)
        token = request.GET.get("token") or request.GET.get("paymentId")
        payer_id = request.GET.get("PayerID") or request.GET.get("payerId")
        if invoice is not None and token:
            try:
                PaymentService.capture_paypal_payment(
                    invoice_id,
                    order_id=token,
                    payer_id=payer_id,
                    created_by=_authenticated_user(request),
                )
                messages.success(request, "Thanh toán PayPal đã được xác nhận và hóa đơn đã được thanh toán.")
            except ValueError as exc:
                logger.warning("dashboard.paypal_capture_failed invoice=%s token=%s error=%s", invoice_id, token, exc)
                messages.warning(request, str(exc))
        if invoice is not None:
            successful_amount = sum(
                (payment.amount for payment in invoice.payments.all() if payment.status == PaymentStatus.SUCCESS),
                Decimal("0"),
            )
            if successful_amount >= invoice.total_amount and invoice.status != InvoiceStatus.PAID:
                InvoiceService.transition(invoice_id, InvoiceStatus.PAID, _authenticated_user(request))
                messages.success(request, "Thanh toán đã được đồng bộ và hóa đơn đã được thanh toán.")
            elif invoice.status == InvoiceStatus.PENDING_PAYMENT:
                messages.info(request, "Hóa đơn đang chờ thanh toán. Đơn hàng đã được cập nhật lại.")
        if invoice is not None and invoice.order_id:
            return redirect("dashboard:order-detail", order_id=invoice.order_id)
    except (Invoice.DoesNotExist, ValueError):
        logger.warning("dashboard.invoice_return_failed invoice=%s", invoice_id)
    return redirect("dashboard:invoice-detail", invoice_id=invoice_id)


@require_permission("view", "invoice")
def payment_status(request: HttpRequest, payment_id: UUID) -> JsonResponse:
    payment = Payment.objects.select_related("invoice").filter(id=payment_id).first()
    if payment is None:
        return JsonResponse({"status": "NOT_FOUND"}, status=404)
    response = {
        "status": payment.status,
        "invoice_status": payment.invoice.status,
        "order_url": "",
    }
    if payment.invoice.order_id:
        response["order_url"] = reverse(
            "dashboard:order-detail", kwargs={"order_id": payment.invoice.order_id}
        )
    return JsonResponse(response)


@require_POST
@require_permission("approve", "payment")
def invoice_manual(request: HttpRequest, invoice_id: UUID) -> HttpResponse:
    try:
        amount = Decimal(request.POST.get("amount", "0"))
        PaymentService.create_manual_payment(
            invoice_id,
            amount=amount,
            reference=request.POST.get("reference", ""),
            note=request.POST.get("note", ""),
            created_by=_authenticated_user(request),
        )
        messages.success(request, "Đã ghi nhận thanh toán thủ công.")
    except (Invoice.DoesNotExist, InvalidOperation, ValueError):
        messages.error(request, "Dữ liệu thanh toán thủ công không hợp lệ.")
    return redirect("dashboard:invoice-detail", invoice_id=invoice_id)


@require_POST
@require_permission("update", "payment")
def payment_cancel(request: HttpRequest, payment_id: UUID) -> HttpResponse:
    try:
        PaymentService.cancel_payment(
            payment_id, cancelled_by=_authenticated_user(request)
        )
        messages.success(request, "Đã hủy thanh toán.")
    except (Payment.DoesNotExist, ValueError):
        messages.error(request, "Không thể hủy thanh toán này.")


# =============================================================================
# Reports
# =============================================================================


def _report_filter(request: HttpRequest) -> ReportFilterForm:
    """Bind and validate the shared Report filter from query params.

    Always bound to `request.GET` (never `None`) — every field is optional,
    so an empty querystring (first visit, no filters chosen yet) still runs
    `ReportFilterForm.clean()` and resolves the default 30-day range, instead
    of leaving the form "unbound" (which `is_valid()` always fails).
    """
    form = ReportFilterForm(request.GET)
    form.is_valid()
    return form


@require_permission("view", "report")
def report_dashboard(request: HttpRequest) -> HttpResponse:
    """Render an overview of every Report type for the selected date range.

    GET /reports/
    """
    form = _report_filter(request)
    context: dict[str, Any] = {"form": form}
    if form.is_valid():
        date_from = form.cleaned_data["date_from"]
        date_to = form.cleaned_data["date_to"]
        top_n = form.cleaned_data["top_n"]
        sort_by = form.cleaned_data["sort_by"]
        # Re-render unbound with the *resolved* values (defaults filled in by
        # clean()), so the widgets show what is actually displayed below —
        # a bound form would otherwise echo back the raw (possibly empty)
        # querystring instead of the resolved date range.
        context["form"] = ReportFilterForm(
            initial={
                "date_from": date_from,
                "date_to": date_to,
                "top_n": top_n,
                "sort_by": sort_by,
            }
        )
        context.update(
            {
                "date_from": date_from,
                "date_to": date_to,
                "top_n": top_n,
                "sort_by": sort_by,
                "revenue": ReportSelector.get_revenue_report(date_from, date_to),
                "top_selling_products": ReportSelector.get_top_selling_products(
                    date_from, date_to, top_n, sort_by
                ),
                "inventory_report": ReportSelector.get_inventory_report(
                    date_from, date_to
                ),
                "payment_breakdown": ReportSelector.get_payment_breakdown(
                    date_from, date_to
                ),
                "customer_report": ReportSelector.get_customer_report(
                    date_from, date_to, top_n
                ),
                "can_export": PermissionSelector.user_has_permission(
                    _authenticated_user(request), "export", "report"
                ),
            }
        )
    return render(request, "dashboard/reports/index.html", context)


@require_permission("export", "report")
def report_revenue_export(request: HttpRequest) -> HttpResponse:
    """Export the revenue report as CSV."""
    form = _report_filter(request)
    if not form.is_valid():
        messages.error(request, "Khoảng thời gian không hợp lệ.")
        return redirect("dashboard:report-dashboard")
    data = ReportSelector.get_revenue_report(
        form.cleaned_data["date_from"], form.cleaned_data["date_to"]
    )
    header, rows = report_exports.revenue_csv(data)
    return report_exports.build_csv_response("bao_cao_doanh_thu.csv", header, rows)


@require_permission("export", "report")
def report_top_selling_export(request: HttpRequest) -> HttpResponse:
    """Export the top-selling products report as CSV."""
    form = _report_filter(request)
    if not form.is_valid():
        messages.error(request, "Khoảng thời gian không hợp lệ.")
        return redirect("dashboard:report-dashboard")
    data = ReportSelector.get_top_selling_products(
        form.cleaned_data["date_from"],
        form.cleaned_data["date_to"],
        form.cleaned_data["top_n"],
        form.cleaned_data["sort_by"],
    )
    header, rows = report_exports.top_selling_products_csv(data)
    return report_exports.build_csv_response(
        "bao_cao_san_pham_ban_chay.csv", header, rows
    )


@require_permission("export", "report")
def report_inventory_export(request: HttpRequest) -> HttpResponse:
    """Export the inventory report as CSV."""
    form = _report_filter(request)
    if not form.is_valid():
        messages.error(request, "Khoảng thời gian không hợp lệ.")
        return redirect("dashboard:report-dashboard")
    data = ReportSelector.get_inventory_report(
        form.cleaned_data["date_from"], form.cleaned_data["date_to"]
    )
    header, rows = report_exports.inventory_csv(data)
    return report_exports.build_csv_response("bao_cao_ton_kho.csv", header, rows)


@require_permission("export", "report")
def report_payment_breakdown_export(request: HttpRequest) -> HttpResponse:
    """Export the payment method/provider breakdown report as CSV."""
    form = _report_filter(request)
    if not form.is_valid():
        messages.error(request, "Khoảng thời gian không hợp lệ.")
        return redirect("dashboard:report-dashboard")
    data = ReportSelector.get_payment_breakdown(
        form.cleaned_data["date_from"], form.cleaned_data["date_to"]
    )
    header, rows = report_exports.payment_breakdown_csv(data)
    return report_exports.build_csv_response(
        "bao_cao_phuong_thuc_thanh_toan.csv", header, rows
    )


@require_permission("export", "report")
def report_customers_export(request: HttpRequest) -> HttpResponse:
    """Export the customer report as CSV."""
    form = _report_filter(request)
    if not form.is_valid():
        messages.error(request, "Khoảng thời gian không hợp lệ.")
        return redirect("dashboard:report-dashboard")
    data = ReportSelector.get_customer_report(
        form.cleaned_data["date_from"],
        form.cleaned_data["date_to"],
        form.cleaned_data["top_n"],
    )
    header, rows = report_exports.customer_report_csv(data)
    return report_exports.build_csv_response("bao_cao_khach_hang.csv", header, rows)
    return redirect("dashboard:invoice-list")


def _insight_response(
    request: HttpRequest, report_type: str, data: Any, cache_key_params: dict[str, Any]
) -> HttpResponse:
    """Shared tail for every `report_*_insights` view below."""
    insight = ReportInsightService.generate(report_type, data, cache_key_params)
    return JsonResponse(insight)


@require_permission("view", "report")
def report_revenue_insights(request: HttpRequest) -> HttpResponse:
    """GET /reports/revenue/insights/ — called by the "Phân tích AI" button."""
    form = _report_filter(request)
    if not form.is_valid():
        return JsonResponse({"error": "invalid_date_range"}, status=400)
    date_from = form.cleaned_data["date_from"]
    date_to = form.cleaned_data["date_to"]
    data = ReportSelector.get_revenue_report(date_from, date_to)
    return _insight_response(
        request, ReportType.REVENUE, data, {"date_from": date_from, "date_to": date_to}
    )


@require_permission("view", "report")
def report_top_selling_insights(request: HttpRequest) -> HttpResponse:
    """GET /reports/products/top-selling/insights/"""
    form = _report_filter(request)
    if not form.is_valid():
        return JsonResponse({"error": "invalid_date_range"}, status=400)
    params = {
        "date_from": form.cleaned_data["date_from"],
        "date_to": form.cleaned_data["date_to"],
        "top_n": form.cleaned_data["top_n"],
        "sort_by": form.cleaned_data["sort_by"],
    }
    data = ReportSelector.get_top_selling_products(**params)
    return _insight_response(request, ReportType.TOP_SELLING_PRODUCTS, data, params)


@require_permission("view", "report")
def report_inventory_insights(request: HttpRequest) -> HttpResponse:
    """GET /reports/inventory/insights/"""
    form = _report_filter(request)
    if not form.is_valid():
        return JsonResponse({"error": "invalid_date_range"}, status=400)
    date_from = form.cleaned_data["date_from"]
    date_to = form.cleaned_data["date_to"]
    data = ReportSelector.get_inventory_report(date_from, date_to)
    return _insight_response(
        request,
        ReportType.INVENTORY,
        data,
        {"date_from": date_from, "date_to": date_to},
    )


@require_permission("view", "report")
def report_payment_breakdown_insights(request: HttpRequest) -> HttpResponse:
    """GET /reports/payments/breakdown/insights/"""
    form = _report_filter(request)
    if not form.is_valid():
        return JsonResponse({"error": "invalid_date_range"}, status=400)
    date_from = form.cleaned_data["date_from"]
    date_to = form.cleaned_data["date_to"]
    data = ReportSelector.get_payment_breakdown(date_from, date_to)
    return _insight_response(
        request,
        ReportType.PAYMENT_BREAKDOWN,
        data,
        {"date_from": date_from, "date_to": date_to},
    )


@require_permission("view", "report")
def report_customers_insights(request: HttpRequest) -> HttpResponse:
    """GET /reports/customers/insights/"""
    form = _report_filter(request)
    if not form.is_valid():
        return JsonResponse({"error": "invalid_date_range"}, status=400)
    params = {
        "date_from": form.cleaned_data["date_from"],
        "date_to": form.cleaned_data["date_to"],
        "top_n": form.cleaned_data["top_n"],
    }
    data = ReportSelector.get_customer_report(**params)
    return _insight_response(request, ReportType.CUSTOMER, data, params)
