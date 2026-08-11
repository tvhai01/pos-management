"""Business exceptions for Product and Category operations."""

from rest_framework import status

from apps.product.constants import (
    MSG_CATEGORY_HAS_PRODUCTS,
    MSG_CATEGORY_NOT_FOUND,
    MSG_PRODUCT_NOT_FOUND,
)
from shared.exceptions import ApplicationError


class ProductNotFoundError(ApplicationError):
    """Raised when a live Product cannot be found."""

    status_code: int = status.HTTP_404_NOT_FOUND
    default_detail: str = MSG_PRODUCT_NOT_FOUND
    default_code: str = "product_not_found"


class CategoryNotFoundError(ApplicationError):
    """Raised when a live Category cannot be found."""

    status_code: int = status.HTTP_404_NOT_FOUND
    default_detail: str = MSG_CATEGORY_NOT_FOUND
    default_code: str = "category_not_found"


class CategoryHasProductsError(ApplicationError):
    """Raised when deleting a Category that still has live Products."""

    status_code: int = status.HTTP_409_CONFLICT
    default_detail: str = MSG_CATEGORY_HAS_PRODUCTS
    default_code: str = "category_has_products"
