"""
Template context processors for the Dashboard UI.

Injects data needed by `base.html` on every page — currently just the
permission-gated navigation list, so every page (not only the ones that
happen to build it themselves) can render a persistent top nav.
"""

from typing import Any

from django.http import HttpRequest

from apps.accounts.selectors import PermissionSelector
from apps.dashboard.nav import NAV_MODULES


def nav_modules(request: HttpRequest) -> dict[str, Any]:
    """Return the permission-gated list of modules for the top navigation.

    Anonymous requests (e.g. the login page) get an empty list — `base.html`
    only renders the nav when `user.is_authenticated`, this just avoids an
    unnecessary permission check per module on those pages.

    Args:
        request: The current request.

    Returns:
        A dict with a single `nav_modules` key for the template context.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"nav_modules": []}

    modules = [
        {
            "key": module["key"],
            "name": module["name"],
            "url_name": module["url_name"],
            "available": PermissionSelector.user_has_permission(
                user, "view", module["resource"]
            ),
        }
        for module in NAV_MODULES
    ]
    return {"nav_modules": modules}
