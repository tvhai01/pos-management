"""Thin REST API views for Product and Category management."""

from typing import Any, cast

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from apps.accounts.models import User
from apps.accounts.permissions import HasPermission
from apps.product.constants import (
    CATEGORY_ORDERING_FIELDS,
    CATEGORY_SEARCH_FIELDS,
    MSG_CATEGORY_CREATED,
    MSG_CATEGORY_DELETED,
    MSG_CATEGORY_NOT_FOUND,
    MSG_CATEGORY_UPDATED,
    MSG_PRODUCT_CREATED,
    MSG_PRODUCT_DELETED,
    MSG_PRODUCT_NOT_FOUND,
    MSG_PRODUCT_UPDATED,
    PRODUCT_ORDERING_FIELDS,
    PRODUCT_SEARCH_FIELDS,
)
from apps.product.permissions import (
    CATEGORY_CREATE_PERMISSION,
    CATEGORY_DELETE_PERMISSION,
    CATEGORY_UPDATE_PERMISSION,
    CATEGORY_VIEW_PERMISSION,
    PRODUCT_CREATE_PERMISSION,
    PRODUCT_DELETE_PERMISSION,
    PRODUCT_UPDATE_PERMISSION,
    PRODUCT_VIEW_PERMISSION,
)
from apps.product.selectors import CategorySelector, ProductSelector
from apps.product.serializers import (
    CategoryDetailSerializer,
    CreateCategorySerializer,
    CreateProductSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    UpdateCategorySerializer,
    UpdateProductSerializer,
)
from apps.product.services import CategoryService, ProductService
from shared.pagination import paginated_success_response
from shared.response import error_response, success_response


def _authenticated_user(request: Request) -> User:
    """Narrow request.user after IsAuthenticated permission checking."""
    return cast(User, request.user)


class ProductListCreateView(GenericAPIView):
    """List/search/filter products or create a product."""

    permission_classes = (IsAuthenticated, HasPermission)
    serializer_class = ProductListSerializer
    filterset_fields: tuple[str, ...] = ("category", "status", "unit")
    search_fields: tuple[str, ...] = PRODUCT_SEARCH_FIELDS
    ordering_fields: tuple[str, ...] = PRODUCT_ORDERING_FIELDS
    ordering: tuple[str, ...] = ("-created_at",)

    def get_queryset(self) -> Any:
        """Return the live Product base queryset."""
        return ProductSelector.get_all_products()

    def get(self, request: Request) -> Any:
        """Return a paginated, filterable Product list."""
        return paginated_success_response(
            view=self,
            queryset=self.get_queryset(),
            serializer_class=ProductListSerializer,
        )

    def post(self, request: Request) -> Any:
        """Validate and create a Product."""
        serializer = CreateProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = ProductService.create_product(
            **serializer.validated_data,
            created_by=_authenticated_user(request),
        )
        return success_response(
            data=ProductDetailSerializer(product).data,
            message=MSG_PRODUCT_CREATED,
            status_code=status.HTTP_201_CREATED,
        )

    def check_permissions(self, request: Request) -> None:
        """Select Product permission based on HTTP method."""
        self.required_permission = (
            PRODUCT_CREATE_PERMISSION
            if request.method == "POST"
            else PRODUCT_VIEW_PERMISSION
        )
        super().check_permissions(request)


class ProductDetailView(GenericAPIView):
    """Retrieve, update, or soft-delete a Product."""

    permission_classes = (IsAuthenticated, HasPermission)
    serializer_class = ProductDetailSerializer

    def get(self, request: Request, product_id: str) -> Any:
        """Return Product details or a standardized 404."""
        product = ProductSelector.get_product_by_id(product_id)
        if product is None:
            return error_response(
                message=MSG_PRODUCT_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=ProductDetailSerializer(product).data)

    def put(self, request: Request, product_id: str) -> Any:
        """Update mutable Product fields."""
        return self._update(request, product_id)

    def patch(self, request: Request, product_id: str) -> Any:
        """Partially update mutable Product fields."""
        return self._update(request, product_id)

    def _update(self, request: Request, product_id: str) -> Any:
        """Share PUT/PATCH validation and service orchestration."""
        serializer = UpdateProductSerializer(
            data=request.data,
            context={"product_id": product_id},
        )
        serializer.is_valid(raise_exception=True)
        product = ProductService.update_product(
            product_id=product_id,
            updated_by=_authenticated_user(request),
            **serializer.validated_data,
        )
        return success_response(
            data=ProductDetailSerializer(product).data,
            message=MSG_PRODUCT_UPDATED,
        )

    def delete(self, request: Request, product_id: str) -> Any:
        """Soft-delete a Product."""
        ProductService.delete_product(
            product_id=product_id,
            deleted_by=_authenticated_user(request),
        )
        return success_response(message=MSG_PRODUCT_DELETED)

    def check_permissions(self, request: Request) -> None:
        """Select Product permission based on HTTP method."""
        permission_map = {
            "GET": PRODUCT_VIEW_PERMISSION,
            "PUT": PRODUCT_UPDATE_PERMISSION,
            "PATCH": PRODUCT_UPDATE_PERMISSION,
            "DELETE": PRODUCT_DELETE_PERMISSION,
        }
        self.required_permission = permission_map.get(
            request.method or "", PRODUCT_VIEW_PERMISSION
        )
        super().check_permissions(request)


class CategoryListCreateView(GenericAPIView):
    """List/search categories or create a category."""

    permission_classes = (IsAuthenticated, HasPermission)
    serializer_class = CategoryDetailSerializer
    search_fields: tuple[str, ...] = CATEGORY_SEARCH_FIELDS
    ordering_fields: tuple[str, ...] = CATEGORY_ORDERING_FIELDS
    ordering: tuple[str, ...] = ("name",)

    def get_queryset(self) -> Any:
        """Return the live Category base queryset."""
        return CategorySelector.get_all_categories()

    def get(self, request: Request) -> Any:
        """Return a paginated, searchable Category list."""
        return paginated_success_response(
            view=self,
            queryset=self.get_queryset(),
            serializer_class=CategoryDetailSerializer,
        )

    def post(self, request: Request) -> Any:
        """Validate and create a Category."""
        serializer = CreateCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = CategoryService.create_category(
            **serializer.validated_data,
            created_by=_authenticated_user(request),
        )
        return success_response(
            data=CategoryDetailSerializer(category).data,
            message=MSG_CATEGORY_CREATED,
            status_code=status.HTTP_201_CREATED,
        )

    def check_permissions(self, request: Request) -> None:
        """Select Category permission based on HTTP method."""
        self.required_permission = (
            CATEGORY_CREATE_PERMISSION
            if request.method == "POST"
            else CATEGORY_VIEW_PERMISSION
        )
        super().check_permissions(request)


class CategoryDetailView(GenericAPIView):
    """Retrieve, update, or soft-delete a Category."""

    permission_classes = (IsAuthenticated, HasPermission)
    serializer_class = CategoryDetailSerializer

    def get(self, request: Request, category_id: str) -> Any:
        """Return Category details or a standardized 404."""
        category = CategorySelector.get_category_by_id(category_id)
        if category is None:
            return error_response(
                message=MSG_CATEGORY_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=CategoryDetailSerializer(category).data)

    def put(self, request: Request, category_id: str) -> Any:
        """Update mutable Category fields."""
        return self._update(request, category_id)

    def patch(self, request: Request, category_id: str) -> Any:
        """Partially update mutable Category fields."""
        return self._update(request, category_id)

    def _update(self, request: Request, category_id: str) -> Any:
        """Share PUT/PATCH validation and service orchestration."""
        serializer = UpdateCategorySerializer(
            data=request.data,
            context={"category_id": category_id},
        )
        serializer.is_valid(raise_exception=True)
        category = CategoryService.update_category(
            category_id=category_id,
            updated_by=_authenticated_user(request),
            **serializer.validated_data,
        )
        return success_response(
            data=CategoryDetailSerializer(category).data,
            message=MSG_CATEGORY_UPDATED,
        )

    def delete(self, request: Request, category_id: str) -> Any:
        """Soft-delete an empty Category."""
        CategoryService.delete_category(
            category_id=category_id,
            deleted_by=_authenticated_user(request),
        )
        return success_response(message=MSG_CATEGORY_DELETED)

    def check_permissions(self, request: Request) -> None:
        """Select Category permission based on HTTP method."""
        permission_map = {
            "GET": CATEGORY_VIEW_PERMISSION,
            "PUT": CATEGORY_UPDATE_PERMISSION,
            "PATCH": CATEGORY_UPDATE_PERMISSION,
            "DELETE": CATEGORY_DELETE_PERMISSION,
        }
        self.required_permission = permission_map.get(
            request.method or "", CATEGORY_VIEW_PERMISSION
        )
        super().check_permissions(request)
