import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("invoices", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("reference", models.CharField(max_length=64, unique=True)),
                ("provider_reference", models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("currency", models.CharField(default="VND", max_length=3)),
                ("payment_method", models.CharField(choices=[("QR", "QR"), ("MANUAL", "Manual")], max_length=20)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("PROCESSING", "Processing"), ("SUCCESS", "Success"), ("FAILED", "Failed"), ("EXPIRED", "Expired"), ("CANCELLED", "Cancelled")], default="PENDING", max_length=20)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="payment_created", to=settings.AUTH_USER_MODEL)),
                ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="invoices.invoice")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="payment_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "payments_payment", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="PaymentTransaction",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("provider", models.CharField(choices=[("SEPAY", "SePay"), ("MANUAL", "Manual")], max_length=20)),
                ("provider_transaction_id", models.CharField(blank=True, max_length=150, null=True)),
                ("provider_reference", models.CharField(blank=True, max_length=100, null=True)),
                ("transaction_type", models.CharField(choices=[("PAYMENT", "Payment"), ("CAPTURE", "Capture"), ("ADJUSTMENT", "Adjustment")], max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("currency", models.CharField(default="VND", max_length=3)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("PROCESSING", "Processing"), ("SUCCESS", "Success"), ("FAILED", "Failed"), ("EXPIRED", "Expired"), ("CANCELLED", "Cancelled")], max_length=20)),
                ("payment_method", models.CharField(choices=[("QR", "QR"), ("MANUAL", "Manual")], max_length=20)),
                ("transaction_content", models.TextField(blank=True, default="")),
                ("raw_response", models.JSONField(blank=True, default=dict)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transactions", to="invoices.invoice")),
                ("payment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transactions", to="payments.payment")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="paymenttransaction_created", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="paymenttransaction_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "payments_transaction", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="PaymentAudit",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("field_name", models.CharField(max_length=80)),
                ("old_value", models.TextField(blank=True, default="")),
                ("new_value", models.TextField(blank=True, default="")),
                ("reason", models.TextField()),
                ("changed_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="payment_audit_entries", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="paymentaudit_created", to=settings.AUTH_USER_MODEL)),
                ("payment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="audit_entries", to="payments.payment")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="paymentaudit_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "payments_audit", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="payment", index=models.Index(fields=["invoice"], name="idx_payment_invoice")),
        migrations.AddIndex(model_name="payment", index=models.Index(fields=["status"], name="idx_payment_status")),
        migrations.AddIndex(model_name="payment", index=models.Index(fields=["payment_method"], name="idx_payment_method")),
        migrations.AddIndex(model_name="payment", index=models.Index(fields=["created_at"], name="idx_payment_created")),
        migrations.AddIndex(model_name="paymenttransaction", index=models.Index(fields=["payment"], name="idx_transaction_payment")),
        migrations.AddIndex(model_name="paymenttransaction", index=models.Index(fields=["invoice"], name="idx_transaction_invoice")),
        migrations.AddIndex(model_name="paymenttransaction", index=models.Index(fields=["provider"], name="idx_transaction_provider")),
        migrations.AddIndex(model_name="paymenttransaction", index=models.Index(fields=["status"], name="idx_transaction_status")),
        migrations.AddIndex(model_name="paymenttransaction", index=models.Index(fields=["created_at"], name="idx_transaction_created")),
        migrations.AddIndex(model_name="paymentaudit", index=models.Index(fields=["payment", "created_at"], name="idx_payment_audit_created")),
        migrations.AddConstraint(model_name="payment", constraint=models.CheckConstraint(condition=Q(amount__gt=0), name="payment_amount_positive")),
        migrations.AddConstraint(model_name="paymenttransaction", constraint=models.UniqueConstraint(fields=("provider", "provider_transaction_id"), name="uniq_provider_transaction")),
    ]