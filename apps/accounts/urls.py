"""
URL configuration for the Accounts app.

Sprint 0: Health check.
Sprint 1: Authentication + RBAC management.
"""

from django.urls import path

from apps.accounts.views import (
    ChangePasswordView,
    CurrentUserView,
    HealthCheckView,
    LoginView,
    LogoutView,
    PermissionListView,
    RefreshTokenView,
    RoleDetailView,
    RoleListCreateView,
    UserDetailView,
    UserListCreateView,
)

app_name: str = "accounts"

urlpatterns: list = [
    # Health Check
    path("health/", HealthCheckView.as_view(), name="health-check"),
    # Authentication
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/refresh/", RefreshTokenView.as_view(), name="auth-refresh"),
    path("auth/me/", CurrentUserView.as_view(), name="auth-me"),
    path(
        "auth/change-password/",
        ChangePasswordView.as_view(),
        name="auth-change-password",
    ),
    # RBAC — Roles
    path("roles/", RoleListCreateView.as_view(), name="role-list-create"),
    path("roles/<uuid:role_id>/", RoleDetailView.as_view(), name="role-detail"),
    # RBAC — Permissions
    path("permissions/", PermissionListView.as_view(), name="permission-list"),
    # Staff (User Management)
    path("users/", UserListCreateView.as_view(), name="user-list-create"),
    path("users/<uuid:user_id>/", UserDetailView.as_view(), name="user-detail"),
]
