"""URL configuration for the session-authenticated Dashboard UI."""

from django.urls import path

from apps.dashboard import views

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
    path("products/", views.product_list, name="product-list"),
    path("products/create/", views.product_create, name="product-create"),
    path(
        "products/<uuid:product_id>/update/",
        views.product_update,
        name="product-update",
    ),
    path(
        "products/<uuid:product_id>/delete/",
        views.product_delete,
        name="product-delete",
    ),
    path(
        "products/<uuid:product_id>/restore/",
        views.product_restore,
        name="product-restore",
    ),
    path("categories/", views.category_list, name="category-list"),
    path("categories/create/", views.category_create, name="category-create"),
    path(
        "categories/<uuid:category_id>/update/",
        views.category_update,
        name="category-update",
    ),
    path(
        "categories/<uuid:category_id>/delete/",
        views.category_delete,
        name="category-delete",
    ),
    path(
        "categories/<uuid:category_id>/restore/",
        views.category_restore,
        name="category-restore",
    ),
    path("trash/", views.trash, name="trash"),
]
