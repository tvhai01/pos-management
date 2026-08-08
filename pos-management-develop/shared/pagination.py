"""
Pagination classes for the POS Management System.

Provides standard pagination with consistent page-based navigation.
"""

from typing import TYPE_CHECKING, Any

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from shared.response import success_response

if TYPE_CHECKING:
    # Deferred: rest_framework.generics reads DEFAULT_PAGINATION_CLASS
    # (this module) at class-definition time, so importing GenericAPIView
    # at module scope here would create a circular import.
    from rest_framework.generics import GenericAPIView


class StandardPageNumberPagination(PageNumberPagination):
    """Standard page number pagination.

    Defaults:
        page_size: 20 items per page.
        max_page_size: 100 items per page (upper limit).
        page_size_query_param: "page_size" — allows clients to customize.
    """

    page_size: int = 20
    page_size_query_param: str = "page_size"
    max_page_size: int = 100


def paginated_success_response(
    view: "GenericAPIView",
    queryset: Any,
    serializer_class: type[Serializer],
    message: str = "",
) -> Response:
    """Filter, paginate, and serialize a queryset into the standard envelope.

    Applies the view's configured `filter_backends` (search/filter/order)
    before pagination, then wraps DRF's paginated payload
    (count/next/previous/results) inside the project's standard
    success envelope. Shared across list endpoints (Customer today;
    Product, Order, etc. in later sprints) so every module paginates
    the same way.

    Args:
        view: A GenericAPIView instance (provides filter_queryset,
            paginate_queryset, get_paginated_response, paginator,
            and request).
        queryset: The base (unfiltered) queryset.
        serializer_class: The serializer used to represent each item.
        message: Optional success message.

    Returns:
        A success_response with paginated data.
    """
    filtered_queryset = view.filter_queryset(queryset)
    page = view.paginate_queryset(filtered_queryset)

    if page is not None:
        serializer = serializer_class(page, many=True)
        paginated = view.get_paginated_response(serializer.data)
        return success_response(data=paginated.data, message=message)

    serializer = serializer_class(filtered_queryset, many=True)
    return success_response(data=serializer.data, message=message)
