"""
Constants for the Accounts app.

Defines closed enumerations for permission actions and resources
using Django's TextChoices for type safety and DB-level validation.
"""

from django.db import models


class PermissionAction(models.TextChoices):
    """Valid permission actions for RBAC.

    Each permission is a combination of an action and a resource.
    Example: action=CREATE, resource=USER → "Can create users".
    """

    CREATE = "create", "Create"
    READ = "read", "Read"
    UPDATE = "update", "Update"
    DELETE = "delete", "Delete"
    EXPORT = "export", "Export"
    IMPORT = "import_", "Import"
    APPROVE = "approve", "Approve"
    VIEW = "view", "View"


class PermissionResource(models.TextChoices):
    """Valid permission resources for RBAC.

    Represents the business entities that can be controlled
    by the permission system. New modules add their resource here.
    """

    USER = "user", "User"
    ROLE = "role", "Role"
    CUSTOMER = "customer", "Customer"
    PRODUCT = "product", "Product"
    CATEGORY = "category", "Category"
    INVENTORY = "inventory", "Inventory"
    INVOICE = "invoice", "Invoice"
    ORDER = "order", "Order"
    PAYMENT = "payment", "Payment"
    DASHBOARD = "dashboard", "Dashboard"
    REPORT = "report", "Report"


# =============================================================================
# Auth Messages
# =============================================================================

MSG_LOGIN_SUCCESS: str = "Login successful."
MSG_LOGOUT_SUCCESS: str = "Logout successful."
MSG_REFRESH_SUCCESS: str = "Token refreshed successfully."
MSG_PASSWORD_CHANGED: str = "Password changed successfully."
MSG_PROFILE_UPDATED: str = "Profile updated successfully."
MSG_INVALID_CREDENTIALS: str = "Invalid email or password."
MSG_INACTIVE_ACCOUNT: str = "This account has been deactivated."
MSG_TOKEN_INVALID: str = "Token is invalid or expired."
MSG_OLD_PASSWORD_INCORRECT: str = "Old password is incorrect."
MSG_PASSWORD_MISMATCH: str = "New password and confirm password do not match."

# =============================================================================
# Role Constants
# =============================================================================

ROLE_SUPER_ADMIN: str = "Super Admin"
ROLE_STAFF: str = "Staff"

MSG_ROLE_CREATED: str = "Role created successfully."
MSG_ROLE_UPDATED: str = "Role updated successfully."
MSG_ROLE_DELETED: str = "Role deleted successfully."
MSG_ROLE_NOT_FOUND: str = "Role not found."
MSG_ROLE_HAS_USERS: str = "Cannot delete role that has assigned users."
