"""Declarative RBAC mappings for Product and Category resources."""

from apps.accounts.constants import PermissionAction, PermissionResource

PRODUCT_VIEW_PERMISSION: dict[str, str] = {
    "action": PermissionAction.VIEW,
    "resource": PermissionResource.PRODUCT,
}
PRODUCT_CREATE_PERMISSION: dict[str, str] = {
    "action": PermissionAction.CREATE,
    "resource": PermissionResource.PRODUCT,
}
PRODUCT_UPDATE_PERMISSION: dict[str, str] = {
    "action": PermissionAction.UPDATE,
    "resource": PermissionResource.PRODUCT,
}
PRODUCT_DELETE_PERMISSION: dict[str, str] = {
    "action": PermissionAction.DELETE,
    "resource": PermissionResource.PRODUCT,
}
PRODUCT_EXPORT_PERMISSION: dict[str, str] = {
    "action": PermissionAction.EXPORT,
    "resource": PermissionResource.PRODUCT,
}

CATEGORY_VIEW_PERMISSION: dict[str, str] = {
    "action": PermissionAction.VIEW,
    "resource": PermissionResource.CATEGORY,
}
CATEGORY_CREATE_PERMISSION: dict[str, str] = {
    "action": PermissionAction.CREATE,
    "resource": PermissionResource.CATEGORY,
}
CATEGORY_UPDATE_PERMISSION: dict[str, str] = {
    "action": PermissionAction.UPDATE,
    "resource": PermissionResource.CATEGORY,
}
CATEGORY_DELETE_PERMISSION: dict[str, str] = {
    "action": PermissionAction.DELETE,
    "resource": PermissionResource.CATEGORY,
}
