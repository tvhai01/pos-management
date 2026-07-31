"""
Views for the Customers app.

Contains:
- Customer list/create endpoint (search, filter, sort, pagination)
- Customer detail/update/(soft) delete endpoint

Views are thin — all business logic lives in services; all query
logic lives in selectors.
"""

from typing import Any

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from apps.accounts.permissions import HasPermission
from apps.customers.constants import (
    CUSTOMER_ORDERING_FIELDS,
    CUSTOMER_SEARCH_FIELDS,
    MSG_CUSTOMER_CREATED,
    MSG_CUSTOMER_DELETED,
    MSG_CUSTOMER_NOT_FOUND,
    MSG_CUSTOMER_UPDATED,
)
from apps.customers.permissions import (
    CUSTOMER_CREATE_PERMISSION,
    CUSTOMER_DELETE_PERMISSION,
    CUSTOMER_UPDATE_PERMISSION,
    CUSTOMER_VIEW_PERMISSION,
)
from apps.customers.selectors import CustomerSelector
from apps.customers.serializers import (
    CreateCustomerSerializer,
    CustomerDetailSerializer,
    CustomerListSerializer,
    UpdateCustomerSerializer,
)
from apps.customers.services import CustomerService
from shared.pagination import paginated_success_response
from shared.response import error_response, success_response


class CustomerListCreateView(GenericAPIView):
    """List/search customers, or create a new customer.

    GET  /api/v1/customers/  — requires view:customer permission
        Supports:
        - ?search=<text>            (matches customer_code, full_name, phone, email)
        - ?status=active|inactive|blocked
        - ?ordering=full_name,-created_at,...
        - ?page=&page_size=
    POST /api/v1/customers/  — requires create:customer permission
    """

    permission_classes = [IsAuthenticated, HasPermission]
    serializer_class = CustomerListSerializer

    filterset_fields: tuple[str, ...] = ("status",)
    search_fields: tuple[str, ...] = CUSTOMER_SEARCH_FIELDS
    ordering_fields: tuple[str, ...] = CUSTOMER_ORDERING_FIELDS
    ordering: tuple[str, ...] = ("-created_at",)

    def get_queryset(self) -> Any:
        """Return the base (unfiltered) customer queryset."""
        return CustomerSelector.get_all_customers()

    def get(self, request: Request) -> Any:
        """List and search customers with pagination.

        Returns:
            Success response with paginated customer list.
        """
        self.required_permission = CUSTOMER_VIEW_PERMISSION
        return paginated_success_response(
            view=self,
            queryset=self.get_queryset(),
            serializer_class=CustomerListSerializer,
        )

    def post(self, request: Request) -> Any:
        """Create a new customer.

        Args:
            request: Contains customer fields (see CreateCustomerSerializer).

        Returns:
            Success response with the created customer data.
        """
        self.required_permission = CUSTOMER_CREATE_PERMISSION
        serializer = CreateCustomerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer = CustomerService.create_customer(
            **serializer.validated_data,
            created_by=request.user,
        )

        output_serializer = CustomerDetailSerializer(customer)
        return success_response(
            data=output_serializer.data,
            message=MSG_CUSTOMER_CREATED,
            status_code=status.HTTP_201_CREATED,
        )

    def check_permissions(self, request: Request) -> None:
        """Override to set required_permission based on HTTP method."""
        if request.method == "POST":
            self.required_permission = CUSTOMER_CREATE_PERMISSION
        else:
            self.required_permission = CUSTOMER_VIEW_PERMISSION
        super().check_permissions(request)


class CustomerDetailView(GenericAPIView):
    """Retrieve, update, or (soft) delete a customer.

    GET    /api/v1/customers/{id}/  — requires view:customer permission
    PUT    /api/v1/customers/{id}/  — requires update:customer permission
    DELETE /api/v1/customers/{id}/  — requires delete:customer permission
    """

    permission_classes = [IsAuthenticated, HasPermission]
    serializer_class = CustomerDetailSerializer

    def get(self, request: Request, customer_id: str) -> Any:
        """Retrieve a customer by ID.

        Args:
            request: The incoming request.
            customer_id: The customer's UUID.

        Returns:
            Success response with customer details, or 404 if not found.
        """
        self.required_permission = CUSTOMER_VIEW_PERMISSION
        customer = CustomerSelector.get_customer_by_id(customer_id)
        if customer is None:
            return error_response(
                message=MSG_CUSTOMER_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = CustomerDetailSerializer(customer)
        return success_response(data=serializer.data)

    def put(self, request: Request, customer_id: str) -> Any:
        """Update a customer.

        Args:
            request: Contains fields to update.
            customer_id: The customer's UUID.

        Returns:
            Success response with the updated customer data.
        """
        self.required_permission = CUSTOMER_UPDATE_PERMISSION
        serializer = UpdateCustomerSerializer(
            data=request.data,
            context={"customer_id": customer_id},
        )
        serializer.is_valid(raise_exception=True)

        customer = CustomerService.update_customer(
            customer_id=customer_id,
            updated_by=request.user,
            **serializer.validated_data,
        )

        output_serializer = CustomerDetailSerializer(customer)
        return success_response(
            data=output_serializer.data,
            message=MSG_CUSTOMER_UPDATED,
        )

    def delete(self, request: Request, customer_id: str) -> Any:
        """Soft-delete a customer.

        Args:
            request: The incoming request.
            customer_id: The customer's UUID.

        Returns:
            Success response confirming deletion.
        """
        self.required_permission = CUSTOMER_DELETE_PERMISSION
        CustomerService.delete_customer(
            customer_id=customer_id,
            deleted_by=request.user,
        )

        return success_response(message=MSG_CUSTOMER_DELETED)

    def check_permissions(self, request: Request) -> None:
        """Override to set required_permission based on HTTP method."""
        method_permission_map: dict[str, dict[str, str]] = {
            "GET": CUSTOMER_VIEW_PERMISSION,
            "PUT": CUSTOMER_UPDATE_PERMISSION,
            "DELETE": CUSTOMER_DELETE_PERMISSION,
        }
        self.required_permission = method_permission_map.get(
            request.method, CUSTOMER_VIEW_PERMISSION
        )
        super().check_permissions(request)
