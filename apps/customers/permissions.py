"""
Permission mappings for the Customers app.

RBAC enforcement itself is centralized in `apps.accounts.permissions`
(HasPermission). This module only declares the action-resource
mappings for the Customer resource so views stay declarative and no
app hardcodes "customer" action/resource strings.

Usage in views:
    from apps.accounts.permissions import HasPermission
    from apps.customers.permissions import CUSTOMER_VIEW_PERMISSION

    class MyView(APIView):
        permission_classes = [IsAuthenticated, HasPermission]
        required_permission = CUSTOMER_VIEW_PERMISSION
"""

from apps.accounts.constants import PermissionAction, PermissionResource

CUSTOMER_VIEW_PERMISSION: dict[str, str] = {
    "action": PermissionAction.VIEW,
    "resource": PermissionResource.CUSTOMER,
}
CUSTOMER_CREATE_PERMISSION: dict[str, str] = {
    "action": PermissionAction.CREATE,
    "resource": PermissionResource.CUSTOMER,
}
CUSTOMER_UPDATE_PERMISSION: dict[str, str] = {
    "action": PermissionAction.UPDATE,
    "resource": PermissionResource.CUSTOMER,
}
CUSTOMER_DELETE_PERMISSION: dict[str, str] = {
    "action": PermissionAction.DELETE,
    "resource": PermissionResource.CUSTOMER,
}
CUSTOMER_EXPORT_PERMISSION: dict[str, str] = {
    "action": PermissionAction.EXPORT,
    "resource": PermissionResource.CUSTOMER,
}
