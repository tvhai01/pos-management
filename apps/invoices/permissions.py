from apps.accounts.constants import PermissionAction, PermissionResource

INVOICE_VIEW_PERMISSION = {"action": PermissionAction.VIEW, "resource": PermissionResource.INVOICE}
INVOICE_CREATE_PERMISSION = {"action": PermissionAction.CREATE, "resource": PermissionResource.INVOICE}
INVOICE_UPDATE_PERMISSION = {"action": PermissionAction.UPDATE, "resource": PermissionResource.INVOICE}