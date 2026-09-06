from django.contrib import admin

from apps.invoices.models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "customer", "total_amount", "currency", "status", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("invoice_number", "customer__full_name", "customer__phone")
    readonly_fields = ("id", "created_at", "updated_at", "paid_at", "cancelled_at")