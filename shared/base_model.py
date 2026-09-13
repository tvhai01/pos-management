"""
Base models for the POS Management System.

Provides abstract base classes that all business models should inherit from
to ensure consistent audit fields (created_at, updated_at, created_by, updated_by).
"""

import uuid

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base model with automatic timestamp fields.

    Attributes:
        id: UUID primary key, auto-generated.
        created_at: Timestamp of record creation (auto-set, immutable).
        updated_at: Timestamp of last modification (auto-set on every save).
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return string representation using the model's UUID."""
        return str(self.id)


class AuditModel(TimeStampedModel):
    """Abstract base model with audit trail fields.

    Extends TimeStampedModel with created_by and updated_by fields
    to track which user created or last modified the record.

    Attributes:
        created_by: Foreign key to the user who created this record.
        updated_by: Foreign key to the user who last updated this record.
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
        verbose_name="Created By",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated",
        verbose_name="Updated By",
    )

    class Meta(TimeStampedModel.Meta):
        abstract = True
