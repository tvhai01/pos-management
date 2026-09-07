"""Query-param input validation for Report endpoints.

Report has no ORM instance to serialize on output — every Selector method
already returns a plain, JSON-safe dict/list, which the view hands straight
to `success_response`. Only *input* validation belongs here.
"""

from typing import Any

from rest_framework import serializers

from apps.reports.constants import (
    DEFAULT_TOP_N,
    MAX_TOP_N,
    TopSellingSortBy,
)
from apps.reports.validators import resolve_date_range


class ReportDateRangeSerializer(serializers.Serializer):
    """Validate/resolve the `date_from`/`date_to` params shared by every report."""

    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Resolve defaults and reject an inverted range."""
        try:
            date_from, date_to = resolve_date_range(
                attrs.get("date_from"), attrs.get("date_to")
            )
        except ValueError as exc:
            raise serializers.ValidationError({"date_from": str(exc)}) from exc

        attrs["date_from"] = date_from
        attrs["date_to"] = date_to
        return attrs


class TopSellingProductsQuerySerializer(ReportDateRangeSerializer):
    """Date range plus Top-N and sort options for the top-selling report."""

    top_n = serializers.IntegerField(
        required=False, min_value=1, max_value=MAX_TOP_N, default=DEFAULT_TOP_N
    )
    sort_by = serializers.ChoiceField(
        choices=TopSellingSortBy.choices,
        required=False,
        default=TopSellingSortBy.REVENUE,
    )


class CustomerReportQuerySerializer(ReportDateRangeSerializer):
    """Date range plus Top-N for the customer report."""

    top_n = serializers.IntegerField(
        required=False, min_value=1, max_value=MAX_TOP_N, default=DEFAULT_TOP_N
    )
