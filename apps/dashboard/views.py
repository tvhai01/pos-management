"""
Views for the Dashboard app.

Session-authenticated, server-rendered admin UI. Same layering rule as
the DRF API: views stay thin and delegate reads to Selectors, writes to
Services. The only new primitive here is `require_permission` (session
equivalent of DRF's `HasPermission`), plus Django's own `authenticate`/
`login`/`logout` for establishing the session (the session-auth analogue
of `AuthService.login` issuing JWTs).
"""

from typing import Any, cast
from uuid import UUID

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.accounts.selectors import PermissionSelector
from apps.customers.constants import CustomerStatus
from apps.customers.exceptions import CustomerNotFoundError
from apps.customers.selectors import CustomerSelector
from apps.customers.services import CustomerService
from apps.dashboard.decorators import require_permission
from apps.dashboard.forms import CategoryForm, CustomerForm, LoginForm, ProductUIForm
from apps.product.constants import ProductStatus
from apps.product.exceptions import (
    CategoryHasProductsError,
    CategoryNotFoundError,
    ProductNotFoundError,
)
from apps.product.selectors import CategorySelector, ProductSelector
from apps.product.services import CategoryService, ProductService

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
            "can_create": PermissionSelector.user_has_permission(
                _authenticated_user(request), "create", "product"
            ),
            "can_update": PermissionSelector.user_has_permission(
                _authenticated_user(request), "update", "product"
            ),
            "can_delete": PermissionSelector.user_has_permission(
                _authenticated_user(request), "delete", "product"
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
