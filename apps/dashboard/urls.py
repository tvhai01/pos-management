"""
URL configuration for the Dashboard app.

Mounted at the project root (`config/urls.py`), so routes below are
reachable at `/`, `/login/`, `/customers/`, etc.
"""

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
]
