"""Thin REST API views for Inventory balances and movements."""

from typing import Any, cast

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from apps.accounts.models import User
from apps.accounts.permissions import HasPermission
from apps.inventory.constants import (
    INVENTORY_ORDERING_FIELDS,
    INVENTORY_SEARCH_FIELDS,
    MOVEMENT_ORDERING_FIELDS,
    MOVEMENT_SEARCH_FIELDS,
    MSG_INVENTORY_NOT_FOUND,
    MSG_MOVEMENT_CREATED,
    MSG_THRESHOLD_UPDATED,
)
from apps.inventory.permissions import (
    INVENTORY_CREATE_PERMISSION,
    INVENTORY_UPDATE_PERMISSION,
    INVENTORY_VIEW_PERMISSION,
)
from apps.inventory.selectors import InventorySelector, StockMovementSelector
from apps.inventory.serializers import (
    CreateStockMovementSerializer,
    InventorySerializer,
    StockMovementSerializer,
    UpdateThresholdSerializer,
)
from apps.inventory.services import InventoryService
from shared.pagination import paginated_success_response
from shared.response import error_response, success_response


def _authenticated_user(request: Request) -> User:
    """Narrow request.user after IsAuthenticated permission checking."""
    return cast(User, request.user)


class InventoryListView(GenericAPIView):
    """List/search/filter current Product balances."""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = INVENTORY_VIEW_PERMISSION
    serializer_class = InventorySerializer
    filterset_fields: tuple[str, ...] = (
        "product__category",
        "product__status",
    )
    search_fields: tuple[str, ...] = INVENTORY_SEARCH_FIELDS
    ordering_fields: tuple[str, ...] = INVENTORY_ORDERING_FIELDS
    ordering: tuple[str, ...] = ("product__sku",)

    def get_queryset(self) -> Any:
        """Return active Product balances."""
        return InventorySelector.get_all_inventories()

    def get(self, request: Request) -> Any:
        """Return a paginated Inventory list."""
        return paginated_success_response(
            view=self,
            queryset=self.get_queryset(),
            serializer_class=InventorySerializer,
        )


class InventoryDetailView(GenericAPIView):
    """Return one Product's current balance."""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = INVENTORY_VIEW_PERMISSION
    serializer_class = InventorySerializer

    def get(self, request: Request, product_id: str) -> Any:
        """Return Inventory details or a standardized 404."""
        inventory = InventorySelector.get_inventory_by_product_id(product_id)
        if inventory is None:
            return error_response(
                message=MSG_INVENTORY_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=InventorySerializer(inventory).data)


class StockMovementListCreateView(GenericAPIView):
    """List movement history or atomically create a stock movement."""

    permission_classes = (IsAuthenticated, HasPermission)
    serializer_class = StockMovementSerializer
    filterset_fields: tuple[str, ...] = (
        "inventory__product",
        "movement_type",
    )
    search_fields: tuple[str, ...] = MOVEMENT_SEARCH_FIELDS
    ordering_fields: tuple[str, ...] = MOVEMENT_ORDERING_FIELDS
    ordering: tuple[str, ...] = ("-created_at",)

    def get_queryset(self) -> Any:
        """Return the immutable movement ledger."""
        return StockMovementSelector.get_all_movements()

    def get(self, request: Request) -> Any:
        """Return paginated Inventory history."""
        return paginated_success_response(
            view=self,
            queryset=self.get_queryset(),
            serializer_class=StockMovementSerializer,
        )

    def post(self, request: Request) -> Any:
        """Validate and record one stock mutation."""
        serializer = CreateStockMovementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inventory, movement = InventoryService.record_movement(
            **serializer.validated_data,
            created_by=_authenticated_user(request),
        )
        return success_response(
            data={
                "inventory": InventorySerializer(inventory).data,
                "movement": StockMovementSerializer(movement).data,
            },
            message=MSG_MOVEMENT_CREATED,
            status_code=status.HTTP_201_CREATED,
        )

    def check_permissions(self, request: Request) -> None:
        """Select read or create permission based on the method."""
        self.required_permission = (
            INVENTORY_CREATE_PERMISSION
            if request.method == "POST"
            else INVENTORY_VIEW_PERMISSION
        )
        super().check_permissions(request)


class InventoryThresholdUpdateView(GenericAPIView):
    """Update one Product's low-stock warning threshold."""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = INVENTORY_UPDATE_PERMISSION
    serializer_class = UpdateThresholdSerializer

    def patch(self, request: Request, product_id: str) -> Any:
        """Validate and update the threshold under a row lock."""
        serializer = UpdateThresholdSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inventory = InventoryService.update_low_stock_threshold(
            product_id=product_id,
            threshold=serializer.validated_data["low_stock_threshold"],
            updated_by=_authenticated_user(request),
        )
        return success_response(
            data=InventorySerializer(inventory).data,
            message=MSG_THRESHOLD_UPDATED,
        )
