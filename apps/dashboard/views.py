"""
Views for the Dashboard app.

Session-authenticated, server-rendered admin UI. Same layering rule as
the DRF API: views stay thin and delegate reads to Selectors, writes to
Services. The only new primitive here is `require_permission` (session
equivalent of DRF's `HasPermission`), plus Django's own `authenticate`/
`login`/`logout` for establishing the session (the session-auth analogue
of `AuthService.login` issuing JWTs).
"""

from typing import Any

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.accounts.selectors import PermissionSelector
from apps.customers.constants import CustomerStatus
from apps.customers.exceptions import CustomerNotFoundError
from apps.customers.selectors import CustomerSelector
from apps.customers.services import CustomerService
from apps.dashboard.decorators import require_permission
from apps.dashboard.forms import CustomerForm, LoginForm

# =============================================================================
# Auth
# =============================================================================


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
                request.user, "view", "customer"
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
                request.user, "create", "customer"
            ),
            "can_update": PermissionSelector.user_has_permission(
                request.user, "update", "customer"
            ),
            "can_delete": PermissionSelector.user_has_permission(
                request.user, "delete", "customer"
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
        CustomerService.create_customer(**form.cleaned_data, created_by=request.user)
        messages.success(request, "Đã tạo khách hàng thành công.")
        return redirect("dashboard:customer-list")

    return render(
        request,
        "dashboard/customers/form.html",
        {"form": form, "is_edit": False},
    )


@require_permission("update", "customer")
def customer_edit(request: HttpRequest, customer_id: str) -> HttpResponse:
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
                updated_by=request.user,
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
def customer_delete(request: HttpRequest, customer_id: str) -> HttpResponse:
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
                customer_id=customer_id, deleted_by=request.user
            )
            messages.success(request, "Đã xoá khách hàng.")
        except CustomerNotFoundError:
            messages.error(request, "Không tìm thấy khách hàng.")
        return redirect("dashboard:customer-list")

    return render(
        request, "dashboard/customers/confirm_delete.html", {"customer": customer}
    )