"""
Global constants for the POS Management System.

Centralizes magic strings and values used across multiple apps.
Never hardcode these values directly in business logic.
"""

# =============================================================================
# API Versioning
# =============================================================================

API_V1_PREFIX: str = "api/v1"

# =============================================================================
# Pagination
# =============================================================================

DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100

# =============================================================================
# Messages
# =============================================================================

MSG_CREATED: str = "Resource created successfully."
MSG_UPDATED: str = "Resource updated successfully."
MSG_DELETED: str = "Resource deleted successfully."
MSG_NOT_FOUND: str = "Resource not found."
MSG_PERMISSION_DENIED: str = "You do not have permission to perform this action."
MSG_VALIDATION_ERROR: str = "Validation failed."
MSG_SERVER_ERROR: str = "An unexpected error occurred."
MSG_UNAUTHORIZED: str = "Authentication credentials were not provided."
MSG_FORBIDDEN: str = "You do not have permission to perform this action."
