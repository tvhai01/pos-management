"""
Access-control decorators for the Dashboard app.

Session-based views can't use DRF's `HasPermission` (it's a
`rest_framework.permissions.BasePermission`, tied to DRF's request/view
cycle). `require_permission` is the server-rendered equivalent: it calls
the exact same `PermissionSelector.user_has_permission` used by
`HasPermission`, so RBAC rules are defined once and enforced identically
regardless of transport (JSON API vs HTML dashboard).
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.accounts.selectors import PermissionSelector


def require_permission(action: str, resource: str) -> Callable:
    """Require the user to be logged in AND hold `action:resource`.

    Superusers always pass (see `PermissionSelector.user_has_permission`).
    Unauthenticated users are redirected to login; authenticated users
    lacking the permission see a 403 page.

    Args:
        action: The permission action (e.g. "view", "create").
        resource: The permission resource (e.g. "customer").

    Returns:
        A decorator to apply to a Django view function.
    """

    def decorator(
        view_func: Callable[..., HttpResponse],
    ) -> Callable[..., HttpResponse]:
        @login_required(login_url="dashboard:login")
        @wraps(view_func)
        def wrapped_view(
            request: HttpRequest, *args: Any, **kwargs: Any
        ) -> HttpResponse:
            if not PermissionSelector.user_has_permission(
                user=request.user, action=action, resource=resource
            ):
                return render(request, "dashboard/403.html", status=403)
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator
