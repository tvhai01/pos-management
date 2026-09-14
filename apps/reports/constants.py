"""Constants for the Report module.

Report has no model of its own — it only aggregates data already owned by
Invoice, Order/OrderItem, Payment/PaymentTransaction, Inventory/StockMovement,
Product and Customer (see docs/prd_report.md § 6).
"""

from django.db import models

DEFAULT_RANGE_DAYS = 30
DEFAULT_TOP_N = 10
MAX_TOP_N = 100

# Revenue breakdown granularity thresholds (in days), per docs/prd_report.md FR-1.
DAILY_GRANULARITY_MAX_DAYS = 31
WEEKLY_GRANULARITY_MAX_DAYS = 180


class RevenueGranularity(models.TextChoices):
    """Time bucket used to group the revenue breakdown."""

    DAY = "day", "Ngày"
    WEEK = "week", "Tuần"
    MONTH = "month", "Tháng"


class TopSellingSortBy(models.TextChoices):
    """Sort key for the top-selling products report."""

    REVENUE = "revenue", "Doanh thu"
    QUANTITY = "quantity", "Số lượng"


class ReportType(models.TextChoices):
    """Identifies which report a `ReportInsightService.generate` call is for."""

    REVENUE = "revenue", "Doanh thu"
    TOP_SELLING_PRODUCTS = "top_selling_products", "Sản phẩm bán chạy"
    INVENTORY = "inventory", "Tồn kho"
    PAYMENT_BREAKDOWN = "payment_breakdown", "Phương thức thanh toán"
    CUSTOMER = "customer", "Khách hàng"


class AIInsightSource(models.TextChoices):
    """Which layer of the fallback chain actually produced an insight."""

    GEMINI = "gemini", "Gemini"
    GROQ = "groq", "Groq"
    RULE_BASED = "rule_based", "Rule-based"


MSG_INVALID_DATE_RANGE = (
    "Ngày bắt đầu (date_from) phải trước hoặc bằng ngày kết thúc (date_to)."
)
