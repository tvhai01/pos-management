"""Deterministic insight generator — the final link of the AI fallback chain.

Every method takes the exact dict `ReportSelector` returns for that report
and returns `{"summary": str, "recommendations": list[str]}`. Never raises
and never does I/O, so it is always available even with no network/API key
configured (see `apps/reports/services.py::ReportInsightService`).
"""

from decimal import Decimal
from typing import Any

from apps.payments.constants import PaymentStatus
from apps.reports.constants import ReportType

_TOP_PRODUCT_SHARE_WARNING = Decimal("0.5")
_PAYMENT_FAILURE_RATE_WARNING = Decimal("0.1")
_TOP_CUSTOMER_SHARE_WARNING = Decimal("0.5")


def _pct_change(before: Decimal, after: Decimal) -> Decimal | None:
    if before == 0:
        return None
    return (after - before) / before * 100


def _revenue_insight(data: dict[str, Any]) -> dict[str, Any]:
    if data["invoice_count"] == 0:
        return {
            "summary": "Không phát sinh doanh thu nào trong khoảng thời gian đã chọn.",
            "recommendations": [
                "Kiểm tra lại hoạt động bán hàng và các kênh tiếp cận khách hàng "
                "trong kỳ này."
            ],
        }

    breakdown = data["breakdown"]
    recommendations = []
    trend_text = "ổn định"
    if len(breakdown) >= 2:
        mid = len(breakdown) // 2
        first_half = breakdown[:mid] or breakdown[:1]
        second_half = breakdown[mid:]
        before = sum((row["total"] for row in first_half), Decimal("0")) / len(
            first_half
        )
        after = sum((row["total"] for row in second_half), Decimal("0")) / len(
            second_half
        )
        change = _pct_change(before, after)
        if change is not None:
            if change <= -10:
                trend_text = f"giảm khoảng {abs(change):.0f}% so với nửa đầu kỳ"
                recommendations.append(
                    "Doanh thu đang giảm — cân nhắc chạy khuyến mãi hoặc chiến dịch "
                    "marketing để kích cầu."
                )
            elif change >= 10:
                trend_text = f"tăng khoảng {change:.0f}% so với nửa đầu kỳ"
                recommendations.append(
                    "Doanh thu đang tăng — đảm bảo tồn kho đủ đáp ứng để không bỏ lỡ "
                    "đơn hàng."
                )

    recommendations.append(
        "Cân nhắc chương trình bán kèm (upsell/combo) để tăng giá trị trung bình "
        "mỗi hoá đơn."
    )

    return {
        "summary": (
            f"Doanh thu kỳ này đạt {data['total_revenue']:,.0f} đ từ "
            f"{data['invoice_count']} hoá đơn, xu hướng {trend_text}."
        ),
        "recommendations": recommendations[:4],
    }


def _top_selling_insight(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "summary": "Không có sản phẩm nào được bán ra trong khoảng thời gian này.",
            "recommendations": [
                "Xem lại trưng bày/khuyến mãi sản phẩm để thúc đẩy doanh số."
            ],
        }

    total_revenue = sum((row["total_revenue"] for row in rows), Decimal("0"))
    top = rows[0]
    recommendations = []
    if total_revenue > 0:
        share = top["total_revenue"] / total_revenue
        if share >= _TOP_PRODUCT_SHARE_WARNING:
            recommendations.append(
                f"'{top['product_name']}' chiếm {share:.0%} doanh thu top sản phẩm — "
                "rủi ro phụ thuộc 1 SKU, nên đa dạng hoá danh mục bán chạy."
            )
    recommendations.append(
        f"Đảm bảo tồn kho cho '{top['product_name']}' — sản phẩm bán chạy nhất kỳ này."
    )

    return {
        "summary": (
            f"'{top['product_name']}' (SKU {top['product_sku']}) dẫn đầu với "
            f"{top['total_quantity']} sản phẩm bán ra, "
            f"{top['total_revenue']:,.0f} đ doanh thu."
        ),
        "recommendations": recommendations[:4],
    }


def _inventory_insight(data: dict[str, Any]) -> dict[str, Any]:
    recommendations = []
    if data["out_of_stock_count"] > 0:
        recommendations.append(
            f"Có {data['out_of_stock_count']} sản phẩm đã hết hàng — cần nhập gấp "
            "để tránh mất doanh số."
        )
    if data["low_stock_count"] > 0:
        recommendations.append(
            f"Có {data['low_stock_count']} sản phẩm sắp hết — lên kế hoạch nhập "
            "thêm trước khi hết hàng."
        )
    if data["outbound_total"] > data["inbound_total"]:
        recommendations.append(
            "Tốc độ xuất kho đang lớn hơn nhập kho trong kỳ — tồn kho tổng thể "
            "đang giảm."
        )
    if not recommendations:
        recommendations.append("Tồn kho đang ổn định, chưa có sản phẩm cần nhập gấp.")

    return {
        "summary": (
            f"Giá trị tồn kho ước tính {data['inventory_value']:,.0f} đ — "
            f"{data['out_of_stock_count']} sản phẩm hết hàng, "
            f"{data['low_stock_count']} sản phẩm sắp hết."
        ),
        "recommendations": recommendations[:4],
    }


def _failure_rate(row: dict[str, Any]) -> Decimal:
    if row["total_count"] == 0:
        return Decimal("0")
    success_count = sum(
        s["count"] for s in row["by_status"] if s["status"] == PaymentStatus.SUCCESS
    )
    return (row["total_count"] - success_count) / row["total_count"]


def _payment_insight(data: dict[str, Any]) -> dict[str, Any]:
    by_method = data["by_payment_method"]
    if not by_method:
        return {
            "summary": "Không có giao dịch thanh toán nào trong khoảng thời gian này.",
            "recommendations": [
                "Kiểm tra lại luồng thanh toán nếu đây là điều bất thường."
            ],
        }

    recommendations = []
    for row in by_method:
        rate = _failure_rate(row)
        if rate >= _PAYMENT_FAILURE_RATE_WARNING:
            recommendations.append(
                f"Phương thức '{row['key']}' có tỉ lệ thất bại {rate:.0%} — nên "
                "kiểm tra lại cổng thanh toán."
            )

    best = max(by_method, key=lambda row: row["success_amount"])
    recommendations.append(
        f"'{best['key']}' đang thu tiền hiệu quả nhất — cân nhắc khuyến khích "
        "khách hàng dùng kênh này."
    )

    return {
        "summary": (
            f"Ghi nhận {sum(r['total_count'] for r in by_method)} giao dịch qua "
            f"{len(by_method)} phương thức thanh toán trong kỳ."
        ),
        "recommendations": recommendations[:4],
    }


def _customer_insight(data: dict[str, Any]) -> dict[str, Any]:
    top_customers = data["top_customers"]
    recommendations = []
    if top_customers:
        total_spent = sum((row["total_spent"] for row in top_customers), Decimal("0"))
        top = top_customers[0]
        if total_spent > 0:
            share = top["total_spent"] / total_spent
            if share >= _TOP_CUSTOMER_SHARE_WARNING:
                recommendations.append(
                    f"Khách hàng '{top['customer__full_name']}' chiếm {share:.0%} "
                    "chi tiêu top khách hàng — nên có chương trình chăm sóc khách "
                    "hàng thân thiết (VIP)."
                )
    if data["new_customers_count"] == 0:
        recommendations.append(
            "Không có khách hàng mới trong kỳ — cân nhắc chiến dịch thu hút "
            "khách hàng mới."
        )
    else:
        recommendations.append(
            f"Đã có {data['new_customers_count']} khách hàng mới — duy trì kênh "
            "thu hút hiện tại."
        )

    return {
        "summary": (
            f"{data['new_customers_count']} khách hàng mới trong kỳ, "
            f"{len(top_customers)} khách hàng nằm trong top chi tiêu."
        ),
        "recommendations": recommendations[:4],
    }


class RuleBasedInsightGenerator:
    """Statistics-and-thresholds insight generator — no external calls."""

    @staticmethod
    def generate(report_type: str, data: Any) -> dict[str, Any]:
        if report_type == ReportType.REVENUE:
            return _revenue_insight(data)
        if report_type == ReportType.TOP_SELLING_PRODUCTS:
            return _top_selling_insight(data)
        if report_type == ReportType.INVENTORY:
            return _inventory_insight(data)
        if report_type == ReportType.PAYMENT_BREAKDOWN:
            return _payment_insight(data)
        if report_type == ReportType.CUSTOMER:
            return _customer_insight(data)
        raise ValueError(f"Unknown report_type: {report_type}")
