import uuid
from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("customers", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="Invoice",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("invoice_number", models.CharField(max_length=40, unique=True)),
                ("subtotal", models.DecimalField(decimal_places=2, max_digits=14)),
                ("discount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("tax", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("total_amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("currency", models.CharField(default="VND", max_length=3)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("PENDING_PAYMENT", "Pending payment"), ("PAID", "Paid"), ("CANCELLED", "Cancelled")], default="DRAFT", max_length=20)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="invoice_created", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="invoices", to="customers.customer")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="invoice_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "invoices_invoice", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="invoice", index=models.Index(fields=["customer", "status"], name="idx_invoice_customer_status")),
        migrations.AddIndex(model_name="invoice", index=models.Index(fields=["status"], name="idx_invoice_status")),
        migrations.AddConstraint(model_name="invoice", constraint=models.CheckConstraint(condition=Q(subtotal__gte=0), name="invoice_subtotal_nonnegative")),
        migrations.AddConstraint(model_name="invoice", constraint=models.CheckConstraint(condition=Q(discount__gte=0), name="invoice_discount_nonnegative")),
        migrations.AddConstraint(model_name="invoice", constraint=models.CheckConstraint(condition=Q(tax__gte=0), name="invoice_tax_nonnegative")),
        migrations.AddConstraint(model_name="invoice", constraint=models.CheckConstraint(condition=Q(total_amount__gt=0), name="invoice_total_positive")),
    ]