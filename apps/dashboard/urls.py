"""
URL configuration for the Dashboard app.

Mounted at the project root (`config/urls.py`), so routes below are
reachable at `/`, `/login/`, `/customers/`, etc.
"""

from django.urls import path

from apps.dashboard import views
from apps.product.views import (
    trash_view,
    product_list_view,
    product_create_view,
    product_update_view,
    product_soft_delete_view,
    product_restore_view,
    product_hard_delete_view,
    category_list_view,
    category_create_view,
    category_update_view,
    category_soft_delete_view,
    category_restore_view,
    category_hard_delete_view,
)

app_name: str = "dashboard"

urlpatterns: list = [
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("customers/", views.customer_list, name="customer-list"),
    path("customers/create/", views.customer_create, name="customer-create"),
    path(
        "customers/<uuid:customer_id>/edit/",
        views.customer_edit,
        name="customer-edit",
    ),
    path(
        "customers/<uuid:customer_id>/delete/",
        views.customer_delete,
        name="customer-delete",
    ),
    path("trash/", trash_view, name="trash"),

    # Products
    path("products/", product_list_view, name="product-list"),
    path("products/create/", product_create_view, name="product-create"),
    path("products/<uuid:product_id>/update/", product_update_view, name="product-update"),
    path("products/<uuid:product_id>/delete/", product_soft_delete_view, name="product-delete"),
    path("products/<uuid:product_id>/restore/", product_restore_view, name="product-restore"),
    path("products/<uuid:product_id>/hard-delete/", product_hard_delete_view, name="product-hard-delete"),

    # Categories
    path("categories/", category_list_view, name="category-list"),
    path("categories/create/", category_create_view, name="category-create"),
    path("categories/<uuid:category_id>/update/", category_update_view, name="category-update"),
    path("categories/<uuid:category_id>/delete/", category_soft_delete_view, name="category-delete"),
    path("categories/<uuid:category_id>/restore/", category_restore_view, name="category-restore"),
    path("categories/<uuid:category_id>/hard-delete/", category_hard_delete_view, name="category-hard-delete"),

]
