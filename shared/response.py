"""
Standardized API response helpers for the POS Management System.

All API endpoints MUST use these helpers to ensure consistent response format.

Success format:
    {
        "success": true,
        "message": "...",
        "data": { ... }
    }

Error format:
    {
        "success": false,
        "message": "...",
        "errors": { ... }
    }
"""

from typing import Any

from rest_framework import status
from rest_framework.response import Response


def success_response(
    data: Any = None,
    message: str = "",
    status_code: int = status.HTTP_200_OK,
) -> Response:
    """Build a standardized success response.

    Args:
        data: The response payload. Can be a dict, list, or None.
        message: A human-readable success message.
        status_code: HTTP status code (default 200).

    Returns:
        A DRF Response with the standard success envelope.
    """
    return Response(
        {
            "success": True,
            "message": message,
            "data": data,
        },
        status=status_code,
    )


def error_response(
    message: str = "",
    errors: dict[str, Any] | None = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    """Build a standardized error response.

    Args:
        message: A human-readable error message.
        errors: A dict of field-level or detail errors.
        status_code: HTTP status code (default 400).

    Returns:
        A DRF Response with the standard error envelope.
    """
    return Response(
        {
            "success": False,
            "message": message,
            "errors": errors or {},
        },
        status=status_code,
    )
