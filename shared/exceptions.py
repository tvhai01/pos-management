"""
Custom exception handler for the POS Management System.

Wraps DRF's default exception handler to enforce the standard error
response format across all API endpoints.
"""

import logging
from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(
    exc: Exception,
    context: dict[str, Any],
) -> Response | None:
    """Handle exceptions and return standardized error responses.

    Wraps DRF's default exception handler. If DRF handles the exception,
    we reformat it into the project's standard error envelope. Unhandled
    exceptions are logged and returned as 500 errors.

    Args:
        exc: The exception that was raised.
        context: The context dict from the view (contains request, view, etc.).

    Returns:
        A Response with the standard error format, or None if unhandled.
    """
    # Let DRF handle it first
    response = exception_handler(exc, context)

    if response is not None:
        # Reformat DRF's response into our standard envelope
        errors: dict[str, Any] = {}

        if isinstance(response.data, dict):
            errors = response.data
            message = errors.pop("detail", str(exc))
        elif isinstance(response.data, list):
            message = str(exc)
            errors = {"detail": response.data}
        else:
            message = str(response.data)

        response.data = {
            "success": False,
            "message": str(message),
            "errors": errors,
        }
        return response

    # Unhandled exception — log it and return a generic 500 response
    logger.exception(
        "Unhandled exception in %s",
        context.get("view", "unknown"),
        exc_info=exc,
    )

    return Response(
        {
            "success": False,
            "message": "An unexpected error occurred.",
            "errors": {},
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


class ApplicationError(APIException):
    """Base exception for application-level business errors.

    Subclass this for specific business rule violations.

    Attributes:
        status_code: HTTP status code (default 400).
        default_detail: Default error message.
        default_code: Machine-readable error code.
    """

    status_code: int = status.HTTP_400_BAD_REQUEST
    default_detail: str = "A business rule violation occurred."
    default_code: str = "application_error"
