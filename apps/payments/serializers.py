from rest_framework import serializers

from apps.payments.constants import PaymentMethod, PaymentStatus
from apps.payments.models import Payment, PaymentTransaction


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("id", "invoice", "reference", "provider_reference", "amount", "currency", "payment_method", "status", "expires_at", "processed_at", "metadata", "created_at", "updated_at")


class CreatePaymentSerializer(serializers.Serializer):
    invoice_id = serializers.UUIDField()
    return_url = serializers.URLField(required=False, allow_blank=True)


class CreateInvoicePaymentSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(choices=PaymentMethod.values)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0.01, required=False)
    payment_date = serializers.DateTimeField(required=False)
    reference = serializers.CharField(max_length=64, required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)
    payer_information = serializers.CharField(required=False, allow_blank=True)
    return_url = serializers.URLField(required=False, allow_blank=True)


class ManualPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0.01)
    payment_date = serializers.DateTimeField(required=False)
    reference = serializers.CharField(max_length=64, required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)
    payer_information = serializers.CharField(required=False, allow_blank=True)


class WebhookSerializer(serializers.Serializer):
    order_invoice_number = serializers.CharField(required=False, allow_blank=True)
    reference = serializers.CharField(required=False, allow_blank=True)
    transaction_id = serializers.CharField(required=False, allow_blank=True)
    id = serializers.CharField(required=False, allow_blank=True)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    currency = serializers.CharField(max_length=3, required=False)
    status = serializers.ChoiceField(choices=PaymentStatus.values, required=False)
    content = serializers.CharField(required=False, allow_blank=True)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = ("id", "payment", "invoice", "provider", "provider_transaction_id", "provider_reference", "transaction_type", "amount", "currency", "status", "payment_method", "transaction_content", "raw_response", "processed_at", "created_at", "updated_at")