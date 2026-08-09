"""RBAC permission descriptors for Inventory endpoints."""

from apps.accounts.constants import PermissionAction, PermissionResource

INVENTORY_VIEW_PERMISSION = {
    "action": PermissionAction.VIEW,
    "resource": PermissionResource.INVENTORY,
}
INVENTORY_CREATE_PERMISSION = {
    "action": PermissionAction.CREATE,
    "resource": PermissionResource.INVENTORY,
}
INVENTORY_UPDATE_PERMISSION = {
    "action": PermissionAction.UPDATE,
    "resource": PermissionResource.INVENTORY,
}
