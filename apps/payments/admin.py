from django.contrib import admin

from apps.payments.models import Payment, PaymentAudit, PaymentTransaction


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "invoice", "amount", "payment_method", "status", "created_at")
    list_filter = ("status", "payment_method", "currency")
    search_fields = ("reference", "provider_reference", "invoice__invoice_number")
    readonly_fields = ("id", "created_at", "updated_at", "processed_at")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("provider", "provider_transaction_id", "payment", "amount", "status", "created_at")
    list_filter = ("provider", "status", "payment_method")
    search_fields = ("provider_transaction_id", "provider_reference", "payment__reference")
    readonly_fields = tuple(field.name for field in PaymentTransaction._meta.fields)


@admin.register(PaymentAudit)
class PaymentAuditAdmin(admin.ModelAdmin):
    list_display = ("payment", "field_name", "changed_by", "created_at")
    readonly_fields = tuple(field.name for field in PaymentAudit._meta.fields)