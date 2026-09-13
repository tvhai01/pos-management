"""Soft-delete-aware model managers for Product and Category."""

from django.db import models


class ActiveRecordManager(models.Manager):
    """Exclude soft-deleted rows from ordinary application queries."""

    def get_queryset(self) -> models.QuerySet:
        """Return only records that have not been soft-deleted."""
        return super().get_queryset().filter(is_deleted=False)
