from typing import Any

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from apps.accounts.permissions import HasPermission
from apps.invoices.models import Invoice
from apps.invoices.permissions import INVOICE_CREATE_PERMISSION, INVOICE_UPDATE_PERMISSION, INVOICE_VIEW_PERMISSION
from apps.invoices.selectors import InvoiceSelector
from apps.invoices.serializers import CreateInvoiceSerializer, InvoiceSerializer, InvoiceTransitionSerializer
from apps.invoices.services import InvoiceService
from shared.pagination import paginated_success_response
from shared.response import error_response, success_response


class InvoiceListCreateView(GenericAPIView):
    permission_classes = (IsAuthenticated, HasPermission)
    search_fields = ("invoice_number", "customer__full_name", "customer__phone")
    ordering_fields = ("invoice_number", "total_amount", "status", "created_at")

    def get(self, request: Request) -> Any:
        self.required_permission = INVOICE_VIEW_PERMISSION
        return paginated_success_response(view=self, queryset=InvoiceSelector.get_all(), serializer_class=InvoiceSerializer)

    def post(self, request: Request) -> Any:
        self.required_permission = INVOICE_CREATE_PERMISSION
        serializer = CreateInvoiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = InvoiceService.create_invoice(**serializer.validated_data, created_by=request.user)
        return success_response(InvoiceSerializer(invoice).data, status_code=status.HTTP_201_CREATED)

    def check_permissions(self, request: Request) -> None:
        self.required_permission = INVOICE_CREATE_PERMISSION if request.method == "POST" else INVOICE_VIEW_PERMISSION
        super().check_permissions(request)


class InvoiceDetailView(GenericAPIView):
    permission_classes = (IsAuthenticated, HasPermission)

    def get(self, request: Request, invoice_id: str) -> Any:
        self.required_permission = INVOICE_VIEW_PERMISSION
        invoice = InvoiceSelector.get_by_id(invoice_id)
        if invoice is None:
            return error_response("Invoice not found.", status_code=status.HTTP_404_NOT_FOUND)
        payments = list(invoice.payments.values("id", "reference", "amount", "status", "payment_method", "expires_at", "created_at"))
        transactions = list(invoice.transactions.values("id", "provider", "provider_transaction_id", "amount", "currency", "status", "payment_method", "transaction_type", "created_at"))
        paid_amount = sum((item["amount"] for item in invoice.payments.filter(status="SUCCESS")), 0)
        return success_response({"invoice": InvoiceSerializer(invoice).data, "order": invoice.order_id, "payments": payments, "transactions": transactions, "payment_summary": {"total_amount": invoice.total_amount, "paid_amount": paid_amount, "remaining_amount": max(invoice.total_amount - paid_amount, 0), "status": invoice.status}})

    def post(self, request: Request, invoice_id: str) -> Any:
        self.required_permission = INVOICE_UPDATE_PERMISSION
        serializer = InvoiceTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            invoice = InvoiceService.transition(invoice_id, serializer.validated_data["status"], request.user)
        except Invoice.DoesNotExist:
            return error_response("Invoice not found.", status_code=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)
        return success_response(InvoiceSerializer(invoice).data)

    def check_permissions(self, request: Request) -> None:
        self.required_permission = INVOICE_UPDATE_PERMISSION if request.method == "POST" else INVOICE_VIEW_PERMISSION
        super().check_permissions(request)