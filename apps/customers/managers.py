"""
Custom manager for the Customers app.

Provides a default manager that transparently excludes soft-deleted
records, plus an unfiltered manager for admin/audit use cases.
"""

from django.db import models


class CustomerManager(models.Manager):
    """Default manager — excludes soft-deleted customers.

    Used as `Customer.objects`. All standard queries (list, detail,
    search) go through this manager so deleted customers never leak
    into normal application flows.
    """

    def get_queryset(self) -> models.QuerySet:
        """Return the base queryset filtered to non-deleted customers."""
        return super().get_queryset().filter(is_deleted=False)
