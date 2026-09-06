from django.contrib import admin

from apps.orders.models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "product_sku", "unit_price", "quantity", "discount", "tax", "subtotal", "total_amount")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer", "total_amount", "currency", "status", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("order_number", "customer__full_name", "customer__phone")
    readonly_fields = ("id", "created_at", "updated_at", "paid_at", "cancelled_at", "completed_at")
    inlines = (OrderItemInline,)