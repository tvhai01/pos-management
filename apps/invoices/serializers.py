from rest_framework import serializers

from apps.customers.models import Customer
from apps.invoices.constants import InvoiceStatus
from apps.invoices.models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ("id", "invoice_number", "customer", "order", "subtotal", "discount", "tax", "total_amount", "currency", "status", "due_at", "paid_at", "cancelled_at", "created_at", "updated_at")
        read_only_fields = ("id", "order", "total_amount", "paid_at", "cancelled_at", "created_at", "updated_at")


class CreateInvoiceSerializer(serializers.Serializer):
    invoice_number = serializers.CharField(max_length=40)
    customer_id = serializers.PrimaryKeyRelatedField(source="customer", queryset=Customer.objects.all())
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0)
    discount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0, default=0)
    tax = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0, default=0)
    currency = serializers.CharField(max_length=3, default="VND")
    due_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs["subtotal"] - attrs["discount"] + attrs["tax"] <= 0:
            raise serializers.ValidationError("Invoice total must be greater than zero.")
        return attrs


class InvoiceTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=InvoiceStatus.values)