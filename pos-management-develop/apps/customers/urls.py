"""
URL configuration for the Customers app.

Sprint 2: Customer Management.
"""

from django.urls import path

from apps.customers.views import CustomerDetailView, CustomerListCreateView

app_name: str = "customers"

urlpatterns: list = [
    path("customers/", CustomerListCreateView.as_view(), name="customer-list-create"),
    path(
        "customers/<uuid:customer_id>/",
        CustomerDetailView.as_view(),
        name="customer-detail",
    ),
]
