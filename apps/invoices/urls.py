from django.urls import path

from apps.invoices.views import InvoiceDetailView, InvoiceListCreateView

app_name = "invoices"
urlpatterns = [
    path("invoices/", InvoiceListCreateView.as_view(), name="invoice-list-create"),
    path("invoices/<uuid:invoice_id>/", InvoiceDetailView.as_view(), name="invoice-detail"),
]