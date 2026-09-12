"""Read-only aggregate queries backing the Report module.

No model belongs to this app — every method here reads Invoice, Order/
OrderItem, Payment/PaymentTransaction, Inventory/StockMovement, Product and
Customer directly (see docs/prd_report.md § 6/§7: Report depends one-way on
those apps, never the other way around).
"""

from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate, TruncMonth, TruncWeek

from apps.customers.models import Customer
from apps.inventory.constants import StockMovementType
from apps.inventory.models import Inventory, StockMovement
from apps.invoices.constants import InvoiceStatus
from apps.invoices.models import Invoice
from apps.orders.models import OrderItem
from apps.payments.constants import PaymentStatus
from apps.payments.models import PaymentTransaction
from apps.reports.constants import (
    DAILY_GRANULARITY_MAX_DAYS,
    WEEKLY_GRANULARITY_MAX_DAYS,
    RevenueGranularity,
    TopSellingSortBy,
)


def _resolve_granularity(date_from: date, date_to: date) -> tuple[str, type]:
    """Pick the revenue breakdown bucket per docs/prd_report.md FR-1."""
    days = (date_to - date_from).days + 1
    if days <= DAILY_GRANULARITY_MAX_DAYS:
        return RevenueGranularity.DAY, TruncDate
    if days <= WEEKLY_GRANULARITY_MAX_DAYS:
        return RevenueGranularity.WEEK, TruncWeek
    return RevenueGranularity.MONTH, TruncMonth


class ReportSelector:
    """Read-only aggregate queries for every Report type."""

    @staticmethod
    def get_revenue_report(date_from: date, date_to: date) -> dict[str, Any]:
        """Total, average and per-period revenue from Paid invoices."""
        invoices = Invoice.objects.filter(
            status=InvoiceStatus.PAID,
            paid_at__date__gte=date_from,
            paid_at__date__lte=date_to,
        )
        totals = invoices.aggregate(
            total_revenue=Coalesce(Sum("total_amount"), Decimal("0")),
            invoice_count=Count("id"),
        )
        invoice_count: int = totals["invoice_count"]
        total_revenue: Decimal = totals["total_revenue"]
        average_invoice_value = (
            total_revenue / invoice_count if invoice_count else Decimal("0")
        )

        granularity, trunc_fn = _resolve_granularity(date_from, date_to)
        breakdown = list(
            invoices.annotate(period=trunc_fn("paid_at"))
            .values("period")
            .annotate(total=Sum("total_amount"), invoice_count=Count("id"))
            .order_by("period")
        )

        return {
            "date_from": date_from,
            "date_to": date_to,
            "total_revenue": total_revenue,
            "invoice_count": invoice_count,
            "average_invoice_value": average_invoice_value,
            "granularity": granularity,
            "breakdown": breakdown,
        }

    @staticmethod
    def get_top_selling_products(
        date_from: date,
        date_to: date,
        top_n: int,
        sort_by: str,
    ) -> list[dict[str, Any]]:
        """Top products by quantity or revenue, sourced from Paid orders."""
        items = OrderItem.objects.filter(
            order__invoice__status=InvoiceStatus.PAID,
            order__invoice__paid_at__date__gte=date_from,
            order__invoice__paid_at__date__lte=date_to,
        )
        order_field = (
            "-total_quantity"
            if sort_by == TopSellingSortBy.QUANTITY
            else "-total_revenue"
        )
        rows = (
            items.values("product_sku", "product_name")
            .annotate(
                total_quantity=Sum("quantity"),
                total_revenue=Sum("total_amount"),
            )
            .order_by(order_field)[:top_n]
        )
        return list(rows)

    @staticmethod
    def get_inventory_report(date_from: date, date_to: date) -> dict[str, Any]:
        """Current stock overview plus movement totals for a date range."""
        active_inventory = Inventory.objects.filter(product__is_deleted=False)

        inventory_value = active_inventory.aggregate(
            value=Coalesce(Sum(F("quantity") * F("product__cost_price")), Decimal("0"))
        )["value"]

        low_stock_products = list(
            active_inventory.filter(
                quantity__gt=0, quantity__lte=F("low_stock_threshold")
            )
            .select_related("product")
            .values("product__sku", "product__name", "quantity", "low_stock_threshold")
            .order_by("product__sku")
        )
        out_of_stock_products = list(
            active_inventory.filter(quantity=0)
            .select_related("product")
            .values("product__sku", "product__name", "low_stock_threshold")
            .order_by("product__sku")
        )

        movements = StockMovement.objects.filter(
            created_at__date__gte=date_from, created_at__date__lte=date_to
        )
        movement_totals = {
            row["movement_type"]: row["total"]
            for row in movements.values("movement_type").annotate(
                total=Sum("quantity_delta")
            )
        }

        return {
            "date_from": date_from,
            "date_to": date_to,
            "out_of_stock_count": len(out_of_stock_products),
            "low_stock_count": len(low_stock_products),
            "inventory_value": inventory_value,
            "inbound_total": movement_totals.get(
                StockMovementType.INBOUND, Decimal("0")
            ),
            "outbound_total": movement_totals.get(
                StockMovementType.OUTBOUND, Decimal("0")
            ),
            "adjustment_total": movement_totals.get(
                StockMovementType.ADJUSTMENT, Decimal("0")
            ),
            "low_stock_products": low_stock_products,
            "out_of_stock_products": out_of_stock_products,
        }

    @staticmethod
    def get_payment_breakdown(date_from: date, date_to: date) -> dict[str, Any]:
        """Transaction counts/success amounts grouped by method and provider."""
        transactions = PaymentTransaction.objects.filter(
            processed_at__date__gte=date_from, processed_at__date__lte=date_to
        )
        return {
            "date_from": date_from,
            "date_to": date_to,
            "by_payment_method": _breakdown_by(transactions, "payment_method"),
            "by_provider": _breakdown_by(transactions, "provider"),
        }

    @staticmethod
    def get_customer_report(
        date_from: date, date_to: date, top_n: int
    ) -> dict[str, Any]:
        """Top spenders (by Paid invoices) and new customer count."""
        top_customers = list(
            Invoice.objects.filter(
                status=InvoiceStatus.PAID,
                paid_at__date__gte=date_from,
                paid_at__date__lte=date_to,
            )
            .values("customer_id", "customer__customer_code", "customer__full_name")
            .annotate(total_spent=Sum("total_amount"), invoice_count=Count("id"))
            .order_by("-total_spent")[:top_n]
        )
        new_customers_count = Customer.all_objects.filter(
            created_at__date__gte=date_from, created_at__date__lte=date_to
        ).count()

        return {
            "date_from": date_from,
            "date_to": date_to,
            "top_customers": top_customers,
            "new_customers_count": new_customers_count,
        }


def _breakdown_by(queryset: Any, group_field: str) -> list[dict[str, Any]]:
    """Group a PaymentTransaction queryset by one field with a status breakdown."""
    totals = (
        queryset.values(group_field)
        .annotate(
            total_count=Count("id"),
            success_amount=Coalesce(
                Sum("amount", filter=Q(status=PaymentStatus.SUCCESS)),
                Decimal("0"),
            ),
        )
        .order_by(group_field)
    )

    status_counts: dict[str, list[dict[str, Any]]] = {}
    for row in (
        queryset.values(group_field, "status")
        .annotate(count=Count("id"))
        .order_by(group_field, "status")
    ):
        status_counts.setdefault(row[group_field], []).append(
            {"status": row["status"], "count": row["count"]}
        )

    return [
        {
            "key": row[group_field],
            "total_count": row["total_count"],
            "success_amount": row["success_amount"],
            "by_status": status_counts.get(row[group_field], []),
        }
        for row in totals
    ]
