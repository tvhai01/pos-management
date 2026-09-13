"""
Django admin configuration for the Accounts app.

Registers the custom User model and RBAC models (Role, Permission, UserRole)
with the admin site.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import Permission, Role, User, UserRole


# =============================================================================
# User Admin
# =============================================================================


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for the custom User model.

    Customizes the admin interface for email-based authentication.
    """

    list_display: tuple[str, ...] = (
        "email",
        "full_name",
        "phone",
        "is_active",
        "is_staff",
        "date_joined",
    )
    list_filter: tuple[str, ...] = (
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
        "roles",
    )
    search_fields: tuple[str, ...] = (
        "email",
        "full_name",
        "phone",
    )
    ordering: tuple[str, ...] = ("-date_joined",)

    # Fieldsets for the user detail page
    fieldsets: tuple = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("full_name", "phone")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Important Dates", {"fields": ("last_login",)}),
    )

    # Fieldsets for the user creation page
    add_fieldsets: tuple = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "phone",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )

    readonly_fields: tuple[str, ...] = ("date_joined", "last_login")


# =============================================================================
# Permission Admin
# =============================================================================


class PermissionInline(admin.TabularInline):
    """Inline for assigning permissions to a role."""

    model = Role.permissions.through
    extra = 1
    verbose_name = "Permission"
    verbose_name_plural = "Permissions"


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Admin configuration for the Permission model."""

    list_display: tuple[str, ...] = (
        "name",
        "action",
        "resource",
        "created_at",
    )
    list_filter: tuple[str, ...] = (
        "action",
        "resource",
    )
    search_fields: tuple[str, ...] = (
        "name",
        "action",
        "resource",
    )
    ordering: tuple[str, ...] = ("resource", "action")
    readonly_fields: tuple[str, ...] = ("id", "created_at", "updated_at")


# =============================================================================
# Role Admin
# =============================================================================


class UserRoleInline(admin.TabularInline):
    """Inline for viewing user-role assignments."""

    model = UserRole
    extra = 0
    readonly_fields: tuple[str, ...] = ("assigned_by", "assigned_at")
    verbose_name = "Assigned User"
    verbose_name_plural = "Assigned Users"


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin configuration for the Role model."""

    list_display: tuple[str, ...] = (
        "name",
        "is_active",
        "permission_count",
        "user_count",
        "created_at",
    )
    list_filter: tuple[str, ...] = ("is_active",)
    search_fields: tuple[str, ...] = ("name",)
    filter_horizontal: tuple[str, ...] = ("permissions",)
    inlines = [UserRoleInline]
    readonly_fields: tuple[str, ...] = ("id", "created_at", "updated_at")

    @admin.display(description="Permissions")
    def permission_count(self, obj: Role) -> int:
        """Return the number of permissions assigned to this role."""
        return obj.permissions.count()

    @admin.display(description="Users")
    def user_count(self, obj: Role) -> int:
        """Return the number of users assigned to this role."""
        return obj.users.count()


# =============================================================================
# UserRole Admin
# =============================================================================


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """Admin configuration for the UserRole through model."""

    list_display: tuple[str, ...] = (
        "user",
        "role",
        "assigned_by",
        "assigned_at",
    )
    list_filter: tuple[str, ...] = ("role",)
    search_fields: tuple[str, ...] = (
        "user__email",
        "role__name",
    )
    readonly_fields: tuple[str, ...] = ("id", "assigned_at")
