from django.urls import path

from apps.payments.views import InvoicePaymentCreateView, ManualPaymentView, PaymentCancelView, PaymentDetailView, PaymentListCreateView, PaymentStatusView, PaymentTransactionListView, SePayWebhookView

app_name = "payments"
urlpatterns = [
    path("payments/", PaymentListCreateView.as_view(), name="payment-list-create"),
    path("invoices/<uuid:invoice_id>/payments/", InvoicePaymentCreateView.as_view(), name="invoice-payment-create"),
    path("payments/sepay/webhook/", SePayWebhookView.as_view(), name="sepay-webhook"),
    path("payments/<uuid:payment_id>/", PaymentDetailView.as_view(), name="payment-detail"),
    path("payments/<uuid:payment_id>/cancel/", PaymentCancelView.as_view(), name="payment-cancel"),
    path("payments/<uuid:payment_id>/status/", PaymentStatusView.as_view(), name="payment-status"),
    path("payments/<uuid:payment_id>/transactions/", PaymentTransactionListView.as_view(), name="payment-transactions"),
    path("payments/<uuid:invoice_id>/manual/", ManualPaymentView.as_view(), name="payment-manual"),
]