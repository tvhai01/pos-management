from apps.accounts.constants import PermissionAction, PermissionResource

PAYMENT_VIEW_PERMISSION = {"action": PermissionAction.VIEW, "resource": PermissionResource.PAYMENT}
PAYMENT_CREATE_PERMISSION = {"action": PermissionAction.CREATE, "resource": PermissionResource.PAYMENT}
PAYMENT_UPDATE_PERMISSION = {"action": PermissionAction.UPDATE, "resource": PermissionResource.PAYMENT}
PAYMENT_APPROVE_PERMISSION = {"action": PermissionAction.APPROVE, "resource": PermissionResource.PAYMENT}