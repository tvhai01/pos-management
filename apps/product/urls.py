"""REST API URL configuration for Product and Category resources."""

from django.urls import path

from apps.product.views import (
    CategoryDetailView,
    CategoryListCreateView,
    ProductDetailView,
    ProductListCreateView,
)

app_name: str = "products"

urlpatterns: list = [
    path("products/", ProductListCreateView.as_view(), name="product-list-create"),
    path(
        "products/<uuid:product_id>/",
        ProductDetailView.as_view(),
        name="product-detail",
    ),
    path(
        "categories/",
        CategoryListCreateView.as_view(),
        name="category-list-create",
    ),
    path(
        "categories/<uuid:category_id>/",
        CategoryDetailView.as_view(),
        name="category-detail",
    ),
]
