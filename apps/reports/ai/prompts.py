"""Builds the Vietnamese prompt sent to an AI provider for one report type.

Only aggregate numbers already computed by `ReportSelector` are sent — never
raw customer names (see `_sanitize_customer_report`), since that data leaves
the system boundary to a third-party API.
"""

import json
from decimal import Decimal
from typing import Any

from apps.reports.constants import ReportType

_INSTRUCTIONS = (
    "Bạn là trợ lý phân tích dữ liệu bán hàng cho một cửa hàng POS. "
    "Dựa trên số liệu JSON dưới đây (loại báo cáo: {report_label}), hãy viết "
    "nhận xét ngắn gọn và đề xuất hành động cụ thể bằng tiếng Việt cho quản "
    "lý cửa hàng.\n\n"
    "Số liệu:\n{data_json}\n\n"
    "Trả lời DUY NHẤT bằng một object JSON hợp lệ, không thêm văn bản nào "
    "khác, đúng schema sau:\n"
    '{{"summary": "1-2 câu nhận xét tổng quan", '
    '"recommendations": ["đề xuất 1", "đề xuất 2", "..."]}}\n'
    "Tối đa 4 đề xuất, mỗi đề xuất tối đa 1 câu, cụ thể và có thể hành động "
    "ngay được."
)


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _sanitize_customer_report(data: dict[str, Any]) -> dict[str, Any]:
    """Drop customer names before the payload leaves the system boundary."""
    sanitized = dict(data)
    sanitized["top_customers"] = [
        {
            "customer_code": row.get("customer__customer_code"),
            "total_spent": row.get("total_spent"),
            "invoice_count": row.get("invoice_count"),
        }
        for row in data.get("top_customers", [])
    ]
    return sanitized


_SANITIZERS = {
    ReportType.CUSTOMER: _sanitize_customer_report,
}


def build_prompt(report_type: str, data: dict[str, Any]) -> str:
    sanitizer = _SANITIZERS.get(report_type)
    payload = sanitizer(data) if sanitizer else data
    return _INSTRUCTIONS.format(
        report_label=ReportType(report_type).label,
        data_json=json.dumps(payload, ensure_ascii=False, default=_json_default),
    )
