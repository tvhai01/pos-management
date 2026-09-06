from typing import Any

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request

from apps.accounts.permissions import HasPermission
from apps.payments.constants import PaymentStatus
from apps.payments.models import Payment
from apps.payments.permissions import PAYMENT_APPROVE_PERMISSION, PAYMENT_CREATE_PERMISSION, PAYMENT_UPDATE_PERMISSION, PAYMENT_VIEW_PERMISSION
from apps.payments.selectors import PaymentSelector
from apps.payments.serializers import CreateInvoicePaymentSerializer, CreatePaymentSerializer, ManualPaymentSerializer, PaymentSerializer, TransactionSerializer, WebhookSerializer
from apps.payments.services import PaymentService
from shared.pagination import paginated_success_response
from shared.response import error_response, success_response


class PaymentListCreateView(GenericAPIView):
    permission_classes = (IsAuthenticated, HasPermission)

    def get(self, request: Request) -> Any:
        self.required_permission = PAYMENT_VIEW_PERMISSION
        return paginated_success_response(view=self, queryset=PaymentSelector.get_all(), serializer_class=PaymentSerializer)

    def post(self, request: Request) -> Any:
        self.required_permission = PAYMENT_CREATE_PERMISSION
        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment, checkout = PaymentService.create_qr_payment(**serializer.validated_data, created_by=request.user)
        except (Payment.DoesNotExist, ValueError) as exc:
            return error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)
        return success_response({"payment": PaymentSerializer(payment).data, "checkout": checkout}, status_code=status.HTTP_201_CREATED)

    def check_permissions(self, request: Request) -> None:
        self.required_permission = PAYMENT_CREATE_PERMISSION if request.method == "POST" else PAYMENT_VIEW_PERMISSION
        super().check_permissions(request)


class InvoicePaymentCreateView(GenericAPIView):
    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = PAYMENT_CREATE_PERMISSION

    def post(self, request: Request, invoice_id: str) -> Any:
        serializer = CreateInvoicePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        payment_method = data.pop("payment_method")
        try:
            if payment_method == "QR":
                data.pop("amount", None)
                data.pop("payment_date", None)
                data.pop("reference", None)
                data.pop("note", None)
                data.pop("payer_information", None)
                payment, checkout = PaymentService.create_qr_payment(invoice_id, created_by=request.user, **data)
                return success_response({"payment": PaymentSerializer(payment).data, "checkout": checkout}, status_code=status.HTTP_201_CREATED)
            data.pop("return_url", None)
            if "amount" not in data:
                return error_response("Manual payment amount is required.")
            payment = PaymentService.create_manual_payment(invoice_id, created_by=request.user, **data)
            return success_response(PaymentSerializer(payment).data, status_code=status.HTTP_201_CREATED)
        except (Payment.DoesNotExist, ValueError) as exc:
            return error_response(str(exc))

    def check_permissions(self, request: Request) -> None:
        self.required_permission = PAYMENT_APPROVE_PERMISSION if request.method == "POST" and request.data.get("payment_method") == "MANUAL" else PAYMENT_CREATE_PERMISSION
        super().check_permissions(request)


class PaymentDetailView(GenericAPIView):
    permission_classes = (IsAuthenticated, HasPermission)

    def get(self, request: Request, payment_id: str) -> Any:
        self.required_permission = PAYMENT_VIEW_PERMISSION
        payment = PaymentSelector.get_by_id(payment_id)
        if payment is None:
            return error_response("Payment not found.", status_code=status.HTTP_404_NOT_FOUND)
        return success_response(PaymentSerializer(payment).data)

    def check_permissions(self, request: Request) -> None:
        self.required_permission = PAYMENT_VIEW_PERMISSION
        super().check_permissions(request)


class PaymentCancelView(GenericAPIView):
    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = PAYMENT_UPDATE_PERMISSION

    def post(self, request: Request, payment_id: str) -> Any:
        try:
            payment = PaymentService.cancel_payment(payment_id, cancelled_by=request.user)
        except Payment.DoesNotExist:
            return error_response("Payment not found.", status_code=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return error_response(str(exc))
        return success_response(PaymentSerializer(payment).data)


class ManualPaymentView(GenericAPIView):
    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = PAYMENT_APPROVE_PERMISSION

    def post(self, request: Request, invoice_id: str) -> Any:
        serializer = ManualPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = PaymentService.create_manual_payment(invoice_id, **serializer.validated_data, created_by=request.user)
        except (Payment.DoesNotExist, ValueError) as exc:
            return error_response(str(exc))
        return success_response(PaymentSerializer(payment).data, status_code=status.HTTP_201_CREATED)


class PaymentStatusView(GenericAPIView):
    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = PAYMENT_VIEW_PERMISSION

    def get(self, request: Request, payment_id: str) -> Any:
        payment = PaymentSelector.get_by_id(payment_id)
        if payment is None:
            return error_response("Payment not found.", status_code=status.HTTP_404_NOT_FOUND)
        if payment.status == PaymentStatus.PENDING and payment.expires_at:
            payment = PaymentService.expire_payment(payment.id)
        return success_response({"id": payment.id, "status": payment.status, "expires_at": payment.expires_at})


class PaymentTransactionListView(GenericAPIView):
    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = PAYMENT_VIEW_PERMISSION

    def get(self, request: Request, payment_id: str) -> Any:
        return success_response(TransactionSerializer(PaymentSelector.get_transactions(payment_id), many=True).data)


class SePayWebhookView(GenericAPIView):
    permission_classes = (AllowAny,)

    def post(self, request: Request) -> Any:
        serializer = WebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        signature = request.headers.get("X-SePay-Signature") or request.data.get("signature")
        try:
            transaction = PaymentService.process_webhook(serializer.validated_data, signature)
        except ValueError as exc:
            return error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)
        return success_response(TransactionSerializer(transaction).data)