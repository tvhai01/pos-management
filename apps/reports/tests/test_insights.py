"""Tests for the AI Insight fallback chain: rule-based generator + service."""

import json
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.reports.ai.providers import AIProviderError
from apps.reports.constants import AIInsightSource, ReportType
from apps.reports.insights import RuleBasedInsightGenerator
from apps.reports.services import ReportInsightService

_LOCMEM_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}


class TestRuleBasedInsightGeneratorRevenue:
    def test_no_invoices_reports_no_revenue(self):
        result = RuleBasedInsightGenerator.generate(
            ReportType.REVENUE,
            {
                "invoice_count": 0,
                "total_revenue": Decimal("0"),
                "average_invoice_value": Decimal("0"),
                "breakdown": [],
            },
        )
        assert "không phát sinh doanh thu" in result["summary"].lower()
        assert result["recommendations"]

    def test_declining_trend_is_flagged(self):
        breakdown = [
            {"period": "2026-01-01", "total": Decimal("1000000"), "invoice_count": 5},
            {"period": "2026-01-02", "total": Decimal("900000"), "invoice_count": 4},
            {"period": "2026-01-03", "total": Decimal("300000"), "invoice_count": 2},
            {"period": "2026-01-04", "total": Decimal("200000"), "invoice_count": 1},
        ]
        result = RuleBasedInsightGenerator.generate(
            ReportType.REVENUE,
            {
                "invoice_count": 12,
                "total_revenue": Decimal("2400000"),
                "average_invoice_value": Decimal("200000"),
                "breakdown": breakdown,
            },
        )
        assert any("giảm" in r for r in result["recommendations"])


class TestRuleBasedInsightGeneratorTopSelling:
    def test_empty_list(self):
        result = RuleBasedInsightGenerator.generate(ReportType.TOP_SELLING_PRODUCTS, [])
        assert "không có sản phẩm" in result["summary"].lower()

    def test_dominant_product_is_flagged(self):
        rows = [
            {
                "product_sku": "SKU0001",
                "product_name": "Sản phẩm A",
                "total_quantity": 100,
                "total_revenue": Decimal("9000000"),
            },
            {
                "product_sku": "SKU0002",
                "product_name": "Sản phẩm B",
                "total_quantity": 10,
                "total_revenue": Decimal("500000"),
            },
        ]
        result = RuleBasedInsightGenerator.generate(
            ReportType.TOP_SELLING_PRODUCTS, rows
        )
        assert any("phụ thuộc 1 sku" in r.lower() for r in result["recommendations"])


class TestRuleBasedInsightGeneratorInventory:
    def test_out_of_stock_is_flagged(self):
        result = RuleBasedInsightGenerator.generate(
            ReportType.INVENTORY,
            {
                "out_of_stock_count": 3,
                "low_stock_count": 2,
                "inventory_value": Decimal("50000000"),
                "inbound_total": Decimal("100"),
                "outbound_total": Decimal("400"),
                "adjustment_total": Decimal("0"),
            },
        )
        assert any("hết hàng" in r.lower() for r in result["recommendations"])
        assert any("giảm" in r.lower() for r in result["recommendations"])

    def test_healthy_inventory_has_no_warnings(self):
        result = RuleBasedInsightGenerator.generate(
            ReportType.INVENTORY,
            {
                "out_of_stock_count": 0,
                "low_stock_count": 0,
                "inventory_value": Decimal("50000000"),
                "inbound_total": Decimal("100"),
                "outbound_total": Decimal("50"),
                "adjustment_total": Decimal("0"),
            },
        )
        assert result["recommendations"] == [
            "Tồn kho đang ổn định, chưa có sản phẩm cần nhập gấp."
        ]


class TestRuleBasedInsightGeneratorPayment:
    def test_no_transactions(self):
        result = RuleBasedInsightGenerator.generate(
            ReportType.PAYMENT_BREAKDOWN,
            {"by_payment_method": [], "by_provider": []},
        )
        assert "không có giao dịch" in result["summary"].lower()

    def test_high_failure_rate_is_flagged(self):
        data = {
            "by_payment_method": [
                {
                    "key": "QR",
                    "total_count": 10,
                    "success_amount": Decimal("1000000"),
                    "by_status": [
                        {"status": "SUCCESS", "count": 5},
                        {"status": "FAILED", "count": 5},
                    ],
                }
            ],
            "by_provider": [],
        }
        result = RuleBasedInsightGenerator.generate(ReportType.PAYMENT_BREAKDOWN, data)
        assert any("thất bại" in r.lower() for r in result["recommendations"])


class TestRuleBasedInsightGeneratorCustomer:
    def test_no_new_customers(self):
        result = RuleBasedInsightGenerator.generate(
            ReportType.CUSTOMER,
            {"top_customers": [], "new_customers_count": 0},
        )
        assert any(
            "không có khách hàng mới" in r.lower() for r in result["recommendations"]
        )

    def test_dominant_customer_is_flagged(self):
        data = {
            "top_customers": [
                {
                    "customer__customer_code": "CUS0001",
                    "customer__full_name": "Nguyen Van A",
                    "total_spent": Decimal("9000000"),
                    "invoice_count": 5,
                },
                {
                    "customer__customer_code": "CUS0002",
                    "customer__full_name": "Tran Thi B",
                    "total_spent": Decimal("500000"),
                    "invoice_count": 1,
                },
            ],
            "new_customers_count": 2,
        }
        result = RuleBasedInsightGenerator.generate(ReportType.CUSTOMER, data)
        assert any("vip" in r.lower() for r in result["recommendations"])


class TestReportInsightServiceFallbackChain:
    """Verify Gemini -> Groq -> rule-based, and that results get cached."""

    @pytest.fixture(autouse=True)
    def _locmem_cache(self, settings):
        from django.core.cache import cache

        settings.CACHES = _LOCMEM_CACHE
        cache.clear()

    def test_uses_gemini_when_available(self):
        with (
            patch(
                "apps.reports.services.GeminiProvider.generate",
                return_value=json.dumps(
                    {"summary": "Tóm tắt từ Gemini", "recommendations": ["Đề xuất 1"]}
                ),
            ) as gemini_mock,
            patch("apps.reports.services.GroqProvider.generate") as groq_mock,
        ):
            result = ReportInsightService.generate(
                ReportType.REVENUE,
                {
                    "invoice_count": 0,
                    "total_revenue": Decimal("0"),
                    "average_invoice_value": Decimal("0"),
                    "breakdown": [],
                },
                {"date_from": "2026-01-01", "date_to": "2026-01-31"},
            )
        assert result["source"] == AIInsightSource.GEMINI
        assert result["summary"] == "Tóm tắt từ Gemini"
        gemini_mock.assert_called_once()
        groq_mock.assert_not_called()

    def test_falls_back_to_groq_when_gemini_fails(self):
        with (
            patch(
                "apps.reports.services.GeminiProvider.generate",
                side_effect=AIProviderError("gemini_not_configured"),
            ),
            patch(
                "apps.reports.services.GroqProvider.generate",
                return_value=json.dumps(
                    {"summary": "Tóm tắt từ Groq", "recommendations": ["Đề xuất 1"]}
                ),
            ),
        ):
            result = ReportInsightService.generate(
                ReportType.REVENUE,
                {
                    "invoice_count": 0,
                    "total_revenue": Decimal("0"),
                    "average_invoice_value": Decimal("0"),
                    "breakdown": [],
                },
                {"date_from": "2026-02-01", "date_to": "2026-02-28"},
            )
        assert result["source"] == AIInsightSource.GROQ
        assert result["summary"] == "Tóm tắt từ Groq"

    def test_falls_back_to_rule_based_when_both_providers_fail(self):
        with (
            patch(
                "apps.reports.services.GeminiProvider.generate",
                side_effect=AIProviderError("gemini_not_configured"),
            ),
            patch(
                "apps.reports.services.GroqProvider.generate",
                side_effect=AIProviderError("groq_not_configured"),
            ),
        ):
            result = ReportInsightService.generate(
                ReportType.REVENUE,
                {
                    "invoice_count": 0,
                    "total_revenue": Decimal("0"),
                    "average_invoice_value": Decimal("0"),
                    "breakdown": [],
                },
                {"date_from": "2026-03-01", "date_to": "2026-03-31"},
            )
        assert result["source"] == AIInsightSource.RULE_BASED

    def test_result_is_cached_between_calls(self):
        params = {"date_from": "2026-04-01", "date_to": "2026-04-30"}
        data = {
            "invoice_count": 0,
            "total_revenue": Decimal("0"),
            "average_invoice_value": Decimal("0"),
            "breakdown": [],
        }
        with patch(
            "apps.reports.services.GeminiProvider.generate",
            return_value=json.dumps({"summary": "Once", "recommendations": []}),
        ) as gemini_mock:
            first = ReportInsightService.generate(ReportType.REVENUE, data, params)
            second = ReportInsightService.generate(ReportType.REVENUE, data, params)
        assert first == second
        gemini_mock.assert_called_once()

    def test_malformed_provider_output_falls_back(self):
        with (
            patch(
                "apps.reports.services.GeminiProvider.generate",
                return_value="not valid json",
            ),
            patch(
                "apps.reports.services.GroqProvider.generate",
                side_effect=AIProviderError("groq_not_configured"),
            ),
        ):
            result = ReportInsightService.generate(
                ReportType.REVENUE,
                {
                    "invoice_count": 0,
                    "total_revenue": Decimal("0"),
                    "average_invoice_value": Decimal("0"),
                    "breakdown": [],
                },
                {"date_from": "2026-05-01", "date_to": "2026-05-31"},
            )
        assert result["source"] == AIInsightSource.RULE_BASED
