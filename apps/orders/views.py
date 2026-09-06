from typing import Any

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from apps.accounts.permissions import HasPermission
from apps.orders.models import Order
from apps.orders.permissions import ORDER_CREATE_PERMISSION, ORDER_UPDATE_PERMISSION, ORDER_VIEW_PERMISSION
from apps.orders.selectors import OrderSelector
from apps.orders.serializers import CreateOrderSerializer, OrderSerializer, OrderTransitionSerializer
from apps.orders.services import OrderService
from shared.pagination import paginated_success_response
from shared.response import error_response, success_response


class OrderListCreateView(GenericAPIView):
    permission_classes = (IsAuthenticated, HasPermission)
    search_fields = ("order_number", "customer__full_name", "customer__phone")
    ordering_fields = ("order_number", "total_amount", "status", "created_at")

    def get(self, request: Request) -> Any:
        self.required_permission = ORDER_VIEW_PERMISSION
        return paginated_success_response(view=self, queryset=OrderSelector.get_all(), serializer_class=OrderSerializer)

    def post(self, request: Request) -> Any:
        self.required_permission = ORDER_CREATE_PERMISSION
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order, invoice = OrderService.create_order(**serializer.validated_data, created_by=request.user)
        except ValueError as exc:
            return error_response(str(exc))
        return success_response({"order": OrderSerializer(order).data, "invoice_id": invoice.id}, status_code=status.HTTP_201_CREATED)

    def check_permissions(self, request: Request) -> None:
        self.required_permission = ORDER_CREATE_PERMISSION if request.method == "POST" else ORDER_VIEW_PERMISSION
        super().check_permissions(request)


class OrderDetailView(GenericAPIView):
    permission_classes = (IsAuthenticated, HasPermission)

    def get(self, request: Request, order_id: str) -> Any:
        self.required_permission = ORDER_VIEW_PERMISSION
        order = OrderSelector.get_by_id(order_id)
        if order is None:
            return error_response("Order not found.", status_code=status.HTTP_404_NOT_FOUND)
        return success_response(OrderSerializer(order).data)

    def post(self, request: Request, order_id: str) -> Any:
        self.required_permission = ORDER_UPDATE_PERMISSION
        serializer = OrderTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = OrderService.transition(order_id, serializer.validated_data["status"], request.user)
        except Order.DoesNotExist:
            return error_response("Order not found.", status_code=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return error_response(str(exc))
        return success_response(OrderSerializer(order).data)

    def check_permissions(self, request: Request) -> None:
        self.required_permission = ORDER_UPDATE_PERMISSION if request.method == "POST" else ORDER_VIEW_PERMISSION
        super().check_permissions(request)