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
        ("product", "0002_alter_product_options_category_is_deleted_and_more"),
    ]
    operations = [
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("order_number", models.CharField(max_length=40, unique=True)),
                ("subtotal", models.DecimalField(decimal_places=2, max_digits=14)),
                ("discount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("tax", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("total_amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("currency", models.CharField(default="VND", max_length=3)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("PENDING_PAYMENT", "Pending payment"), ("PAID", "Paid"), ("CANCELLED", "Cancelled"), ("COMPLETED", "Completed")], default="DRAFT", max_length=20)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="order_created", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orders", to="customers.customer")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="order_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "orders_order", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("product_name", models.CharField(max_length=255)),
                ("product_sku", models.CharField(max_length=50)),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=14)),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=12)),
                ("discount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("tax", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=14)),
                ("subtotal", models.DecimalField(decimal_places=2, max_digits=14)),
                ("total_amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="orderitem_created", to=settings.AUTH_USER_MODEL)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="orders.order")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="order_items", to="product.product")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="orderitem_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "orders_order_item", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="order", index=models.Index(fields=["customer", "status"], name="idx_order_customer_status")),
        migrations.AddIndex(model_name="order", index=models.Index(fields=["status"], name="idx_order_status")),
        migrations.AddIndex(model_name="orderitem", index=models.Index(fields=["order"], name="idx_order_item_order")),
        migrations.AddIndex(model_name="orderitem", index=models.Index(fields=["product"], name="idx_order_item_product")),
        migrations.AddConstraint(model_name="order", constraint=models.CheckConstraint(condition=Q(total_amount__gt=0), name="order_total_positive")),
        migrations.AddConstraint(model_name="order", constraint=models.CheckConstraint(condition=Q(subtotal__gte=0), name="order_subtotal_nonnegative")),
        migrations.AddConstraint(model_name="orderitem", constraint=models.CheckConstraint(condition=Q(quantity__gt=0), name="order_item_quantity_positive")),
        migrations.AddConstraint(model_name="orderitem", constraint=models.CheckConstraint(condition=Q(unit_price__gte=0), name="order_item_price_nonnegative")),
    ]