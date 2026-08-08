"""
Django admin configuration for the Customers app.

Registers the Customer model with the admin site.
"""

from django.contrib import admin

from apps.customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Admin configuration for the Customer model.

    Uses `all_objects` so soft-deleted customers remain visible/auditable
    to staff, unlike the default `objects` manager used by the app.
    """

    list_display: tuple[str, ...] = (
        "customer_code",
        "full_name",
        "phone",
        "email",
        "status",
        "is_deleted",
        "created_at",
    )
    list_filter: tuple[str, ...] = (
        "status",
        "gender",
        "is_deleted",
    )
    search_fields: tuple[str, ...] = (
        "customer_code",
        "full_name",
        "phone",
        "email",
    )
    ordering: tuple[str, ...] = ("-created_at",)
    readonly_fields: tuple[str, ...] = (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    def get_queryset(self, request: object) -> object:
        """Use the unfiltered manager so admins can see deleted customers."""
        return Customer.all_objects.all()
