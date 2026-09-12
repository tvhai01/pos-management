"""Shared date-range resolution for Report's Serializer and Form inputs.

One function, reused by `serializers.py` (API) and `apps/dashboard/forms.py`
(Dashboard) so both transports resolve "no date given" the same way —
same pattern as `apps.customers.validators` being shared by
`CreateCustomerSerializer` and `CustomerForm`.
"""

from datetime import date, timedelta

from django.utils import timezone

from apps.reports.constants import DEFAULT_RANGE_DAYS, MSG_INVALID_DATE_RANGE


def resolve_date_range(
    date_from: date | None,
    date_to: date | None,
) -> tuple[date, date]:
    """Fill in missing bounds and validate a report date range.

    Args:
        date_from: Start date, or None to default to `DEFAULT_RANGE_DAYS`
            days before the resolved end date.
        date_to: End date, or None to default to today (local time zone).

    Returns:
        The resolved (date_from, date_to) pair.

    Raises:
        ValueError: If the resolved date_from is after date_to.
    """
    resolved_to = date_to or timezone.localdate()
    resolved_from = date_from or (resolved_to - timedelta(days=DEFAULT_RANGE_DAYS - 1))

    if resolved_from > resolved_to:
        raise ValueError(MSG_INVALID_DATE_RANGE)

    return resolved_from, resolved_to
