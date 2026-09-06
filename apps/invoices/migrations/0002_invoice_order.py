import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0001_initial"),
        ("orders", "0001_initial"),
    ]
    operations = [
        migrations.AddField(
            model_name="invoice",
            name="order",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="invoice", to="orders.order"),
        ),
    ]