"""
Models for the Accounts app.

Defines:
- User: Custom user model with email-based authentication.
- Permission: Granular permission using action-resource pattern.
- Role: Named collection of permissions.
- UserRole: Through model for User-Role M2M with audit trail.
"""

import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.accounts.constants import PermissionAction, PermissionResource
from apps.accounts.managers import UserManager
from shared.base_model import TimeStampedModel


class Permission(TimeStampedModel):
    """Granular permission using action-resource pattern.

    Each permission represents a single allowed operation on a resource.
    Example: action="create", resource="user" → "Can create users".

    Attributes:
        name: Human-readable permission name (e.g., "Create User").
        action: The operation type (from PermissionAction TextChoices).
        resource: The target entity (from PermissionResource TextChoices).
        description: Optional longer description of the permission.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Permission Name",
    )
    action = models.CharField(
        max_length=20,
        choices=PermissionAction.choices,
        verbose_name="Action",
    )
    resource = models.CharField(
        max_length=50,
        choices=PermissionResource.choices,
        verbose_name="Resource",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
    )

    class Meta(TimeStampedModel.Meta):
        db_table = "accounts_permission"
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        ordering = ["resource", "action"]
        constraints = [
            models.UniqueConstraint(
                fields=["action", "resource"],
                name="unique_action_resource",
            ),
        ]
        indexes = [
            models.Index(
                fields=["action", "resource"],
                name="idx_permission_action_resource",
            ),
        ]

    def __str__(self) -> str:
        """Return a readable permission label."""
        return f"{self.get_action_display()} {self.get_resource_display()}"


class Role(TimeStampedModel):
    """Named collection of permissions.

    Roles are assigned to users via the UserRole through model.
    A role can be deactivated (is_active=False) to temporarily
    revoke all its permissions without removing assignments.

    Attributes:
        name: Unique role name (e.g., "Super Admin", "Staff").
        description: Optional description of the role's purpose.
        is_active: Whether this role is currently active.
        permissions: M2M relationship to Permission.
    """

    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Role Name",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
    )
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="roles",
        verbose_name="Permissions",
    )

    class Meta(TimeStampedModel.Meta):
        db_table = "accounts_role"
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ["name"]

    def __str__(self) -> str:
        """Return the role name."""
        return self.name


class UserRole(models.Model):
    """Through model for User-Role M2M relationship.

    Tracks which user was assigned which role, by whom, and when.

    Attributes:
        id: UUID primary key.
        user: The user who receives the role.
        role: The role being assigned.
        assigned_by: The user who performed the assignment (nullable).
        assigned_at: When the role was assigned.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID",
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="user_roles",
        verbose_name="User",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="user_roles",
        verbose_name="Role",
    )
    assigned_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_assignments_made",
        verbose_name="Assigned By",
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Assigned At",
    )

    class Meta:
        db_table = "accounts_user_role"
        verbose_name = "User Role"
        verbose_name_plural = "User Roles"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"],
                name="unique_user_role",
            ),
        ]

    def __str__(self) -> str:
        """Return a readable user-role label."""
        return f"{self.user.email} → {self.role.name}"


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model for the POS Management System.

    Uses email as the unique identifier for authentication.
    Inherits password hashing and permission support from Django's
    AbstractBaseUser and PermissionsMixin.

    Attributes:
        id: UUID primary key.
        email: Unique email address (used as USERNAME_FIELD).
        full_name: User's display name.
        phone: Optional phone number (unique when provided).
        is_active: Whether the user account is active.
        is_staff: Whether the user can access the admin site.
        date_joined: When the user account was created.
        roles: M2M relationship to Role via UserRole.
        created_at: Timestamp of record creation.
        updated_at: Timestamp of last modification.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID",
    )
    email = models.EmailField(
        unique=True,
        max_length=255,
        verbose_name="Email Address",
    )
    full_name = models.CharField(
        max_length=150,
        verbose_name="Full Name",
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="Phone Number",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Designates whether this user should be treated as active.",
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name="Staff Status",
        help_text="Designates whether the user can log into the admin site.",
    )
    date_joined = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date Joined",
    )
    roles = models.ManyToManyField(
        Role,
        through=UserRole,
        through_fields=("user", "role"),
        blank=True,
        related_name="users",
        verbose_name="Roles",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At",
    )

    # Use custom manager
    objects = UserManager()

    # Authentication configuration
    USERNAME_FIELD: str = "email"
    REQUIRED_FIELDS: list[str] = ["full_name"]

    class Meta:
        db_table = "accounts_user"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"], name="idx_user_email"),
            models.Index(fields=["is_active"], name="idx_user_is_active"),
        ]

    def __str__(self) -> str:
        """Return the user's email as the string representation."""
        return self.email

    @property
    def short_name(self) -> str:
        """Return the user's first name or email prefix."""
        if self.full_name:
            return self.full_name.split(" ")[0]
        return self.email.split("@")[0]

    @property
    def role_names(self) -> list[str]:
        """Return a list of active role names assigned to this user."""
        return list(
            self.roles.filter(is_active=True).values_list("name", flat=True)
        )
