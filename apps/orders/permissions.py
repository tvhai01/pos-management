from apps.accounts.constants import PermissionAction, PermissionResource

ORDER_VIEW_PERMISSION = {"action": PermissionAction.VIEW, "resource": PermissionResource.ORDER}
ORDER_CREATE_PERMISSION = {"action": PermissionAction.CREATE, "resource": PermissionResource.ORDER}
ORDER_UPDATE_PERMISSION = {"action": PermissionAction.UPDATE, "resource": PermissionResource.ORDER}