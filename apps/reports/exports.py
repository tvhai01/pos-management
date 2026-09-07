"""CSV formatting for Report exports.

Pure formatting — converts a Selector's dict/list result into CSV rows.
Kept separate from `views.py` so the view stays thin (parse → Selector →
format → response), same spirit as a Serializer formatting JSON output.

`build_csv_response` lives here (not in `views.py`) so both transports build
the exact same file: `apps.reports.views` (JWT API) and `apps.dashboard.views`
(session) both call it — same "one helper, two transports" pattern as
`CustomerSelector` methods reused by the Dashboard forms.
"""

import csv
from typing import Any

from django.http import HttpResponse

CsvTable = tuple[list[str], list[list[Any]]]


def build_csv_response(
    filename: str, header: list[str], rows: list[list[Any]]
) -> HttpResponse:
    """Build a UTF-8 (BOM) CSV attachment response."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("﻿")  # BOM so Excel renders UTF-8 Vietnamese diacritics correctly
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(rows)
    return response


def revenue_csv(data: dict[str, Any]) -> CsvTable:
    """Header + rows for the revenue report."""
    header = ["Kỳ", "Doanh thu", "Số hoá đơn"]
    rows = [
        [row["period"], row["total"], row["invoice_count"]] for row in data["breakdown"]
    ]
    return header, rows


def top_selling_products_csv(rows: list[dict[str, Any]]) -> CsvTable:
    """Header + rows for the top-selling products report."""
    header = ["SKU", "Tên sản phẩm", "Số lượng bán", "Doanh thu"]
    return header, [
        [
            row["product_sku"],
            row["product_name"],
            row["total_quantity"],
            row["total_revenue"],
        ]
        for row in rows
    ]


def inventory_csv(data: dict[str, Any]) -> CsvTable:
    """Header + rows for the low-stock/out-of-stock product list."""
    header = ["SKU", "Tên sản phẩm", "Tồn hiện tại", "Ngưỡng tồn thấp", "Trạng thái"]
    rows: list[list[Any]] = [
        [
            row["product__sku"],
            row["product__name"],
            row["quantity"],
            row["low_stock_threshold"],
            "Tồn thấp",
        ]
        for row in data["low_stock_products"]
    ]
    rows += [
        [
            row["product__sku"],
            row["product__name"],
            0,
            row["low_stock_threshold"],
            "Hết hàng",
        ]
        for row in data["out_of_stock_products"]
    ]
    return header, rows


def payment_breakdown_csv(data: dict[str, Any]) -> CsvTable:
    """Header + rows combining the payment-method and provider breakdowns."""
    header = [
        "Nhóm theo",
        "Giá trị",
        "Tổng số giao dịch",
        "Tiền thu (Success)",
        "Trạng thái",
        "Số lượng",
    ]
    rows: list[list[Any]] = []
    for label, entries in (
        ("Phương thức", data["by_payment_method"]),
        ("Nhà cung cấp", data["by_provider"]),
    ):
        for entry in entries:
            rows.append(
                [
                    label,
                    entry["key"],
                    entry["total_count"],
                    entry["success_amount"],
                    "TỔNG",
                    entry["total_count"],
                ]
            )
            for status_row in entry["by_status"]:
                rows.append(
                    [
                        label,
                        entry["key"],
                        "",
                        "",
                        status_row["status"],
                        status_row["count"],
                    ]
                )
    return header, rows


def customer_report_csv(data: dict[str, Any]) -> CsvTable:
    """Header + rows for the top-customers table."""
    header = ["Mã khách hàng", "Tên khách hàng", "Tổng chi tiêu", "Số hoá đơn"]
    return header, [
        [
            row["customer__customer_code"],
            row["customer__full_name"],
            row["total_spent"],
            row["invoice_count"],
        ]
        for row in data["top_customers"]
    ]
