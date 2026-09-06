from rest_framework import serializers

from apps.customers.models import Customer
from apps.orders.constants import OrderStatus
from apps.orders.models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ("id", "product", "product_name", "product_sku", "unit_price", "quantity", "discount", "tax", "subtotal", "total_amount")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ("id", "order_number", "customer", "subtotal", "discount", "tax", "total_amount", "currency", "status", "paid_at", "cancelled_at", "completed_at", "items", "created_at", "updated_at")


class CreateOrderItemSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=0.001)


class CreateOrderSerializer(serializers.Serializer):
    customer_id = serializers.PrimaryKeyRelatedField(source="customer", queryset=Customer.objects.all())
    items = CreateOrderItemSerializer(many=True, allow_empty=False)
    discount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0, default=0)
    tax = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0, default=0)
    currency = serializers.CharField(max_length=3, default="VND")


class OrderTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OrderStatus.values)