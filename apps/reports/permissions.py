"""RBAC permission descriptors for Report endpoints."""

from apps.accounts.constants import PermissionAction, PermissionResource

REPORT_VIEW_PERMISSION = {
    "action": PermissionAction.VIEW,
    "resource": PermissionResource.REPORT,
}
REPORT_EXPORT_PERMISSION = {
    "action": PermissionAction.EXPORT,
    "resource": PermissionResource.REPORT,
}
