"""Thin REST API views for Report — read-only, no Service layer.

Report has no writes to orchestrate, so there is no Service here (README
§1: Service is for business logic/writes). Every view: parse query params
via a Serializer, call one ReportSelector method, return the result.
"""

from typing import Any

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.permissions import HasPermission
from apps.reports import exports
from apps.reports.constants import ReportType
from apps.reports.exports import build_csv_response
from apps.reports.permissions import REPORT_EXPORT_PERMISSION, REPORT_VIEW_PERMISSION
from apps.reports.selectors import ReportSelector
from apps.reports.serializers import (
    CustomerReportQuerySerializer,
    ReportDateRangeSerializer,
    TopSellingProductsQuerySerializer,
)
from apps.reports.services import ReportInsightService
from shared.response import success_response


class RevenueReportView(APIView):
    """GET /api/v1/reports/revenue/"""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = REPORT_VIEW_PERMISSION

    def get(self, request: Request) -> Any:
        query = ReportDateRangeSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = ReportSelector.get_revenue_report(**query.validated_data)
        return success_response(data=data)


class RevenueInsightView(APIView):
    """GET /api/v1/reports/revenue/insights/"""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = REPORT_VIEW_PERMISSION

    def get(self, request: Request) -> Any:
        query = ReportDateRangeSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = ReportSelector.get_revenue_report(**query.validated_data)
        insight = ReportInsightService.generate(
            ReportType.REVENUE, data, query.validated_data
        )
        return success_response(data=insight)


class RevenueReportExportView(APIView):
    """GET /api/v1/reports/revenue/export/"""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = REPORT_EXPORT_PERMISSION

    def get(self, request: Request) -> Any:
        query = ReportDateRangeSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = ReportSelector.get_revenue_report(**query.validated_data)
        header, rows = exports.revenue_csv(data)
        return build_csv_response("bao_cao_doanh_thu.csv", header, rows)


class TopSellingProductsReportView(APIView):
    """GET /api/v1/reports/products/top-selling/"""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = REPORT_VIEW_PERMISSION

    def get(self, request: Request) -> Any:
        query = TopSellingProductsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = ReportSelector.get_top_selling_products(**query.validated_data)
        return success_response(data=data)


class TopSellingProductsExportView(APIView):
    """GET /api/v1/reports/products/top-selling/export/"""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = REPORT_EXPORT_PERMISSION

    def get(self, request: Request) -> Any:
        query = TopSellingProductsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = ReportSelector.get_top_selling_products(**query.validated_data)
        header, rows = exports.top_selling_products_csv(data)
        return build_csv_response("bao_cao_san_pham_ban_chay.csv", header, rows)


class TopSellingProductsInsightView(APIView):
    """GET /api/v1/reports/products/top-selling/insights/"""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = REPORT_VIEW_PERMISSION

    def get(self, request: Request) -> Any:
        query = TopSellingProductsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = ReportSelector.get_top_selling_products(**query.validated_data)
        insight = ReportInsightService.generate(
            ReportType.TOP_SELLING_PRODUCTS, data, query.validated_data
        )
        return success_response(data=insight)


class InventoryReportView(APIView):
    """GET /api/v1/reports/inventory/"""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = REPORT_VIEW_PERMISSION

    def get(self, request: Request) -> Any:
        query = ReportDateRangeSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = ReportSelector.get_inventory_report(**query.validated_data)
        return success_response(data=data)


class InventoryReportExportView(APIView):
    """GET /api/v1/reports/inventory/export/"""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = REPORT_EXPORT_PERMISSION

    def get(self, request: Request) -> Any:
        query = ReportDateRangeSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = ReportSelector.get_inventory_report(**query.validated_data)
        header, rows = exports.inventory_csv(data)
        return build_csv_response("bao_cao_ton_kho.csv", header, rows)


class InventoryInsightView(APIView):
    """GET /api/v1/reports/inventory/insights/"""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = REPORT_VIEW_PERMISSION

    def get(self, request: Request) -> Any:
        query = ReportDateRangeSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = ReportSelector.get_inventory_report(**query.validated_data)
        insight = ReportInsightService.generate(
            ReportType.INVENTORY, data, query.validated_data
        )
        return success_response(data=insight)


class PaymentBreakdownReportView(APIView):
    """GET /api/v1/reports/payments/breakdown/"""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = REPORT_VIEW_PERMISSION

    def get(self, request: Request) -> Any:
        query = ReportDateRangeSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = ReportSelector.get_payment_breakdown(**query.validated_data)
        return success_response(data=data)


class PaymentBreakdownExportView(APIView):
    """GET /api/v1/reports/payments/breakdown/export/"""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = REPORT_EXPORT_PERMISSION

    def get(self, request: Request) -> Any:
        query = ReportDateRangeSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = ReportSelector.get_payment_breakdown(**query.validated_data)
        header, rows = exports.payment_breakdown_csv(data)
        return build_csv_response("bao_cao_phuong_thuc_thanh_toan.csv", header, rows)


class PaymentBreakdownInsightView(APIView):
    """GET /api/v1/reports/payments/breakdown/insights/"""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = REPORT_VIEW_PERMISSION

    def get(self, request: Request) -> Any:
        query = ReportDateRangeSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = ReportSelector.get_payment_breakdown(**query.validated_data)
        insight = ReportInsightService.generate(
            ReportType.PAYMENT_BREAKDOWN, data, query.validated_data
        )
        return success_response(data=insight)


class CustomerReportView(APIView):
    """GET /api/v1/reports/customers/"""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = REPORT_VIEW_PERMISSION

    def get(self, request: Request) -> Any:
        query = CustomerReportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = ReportSelector.get_customer_report(**query.validated_data)
        return success_response(data=data)


class CustomerReportExportView(APIView):
    """GET /api/v1/reports/customers/export/"""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = REPORT_EXPORT_PERMISSION

    def get(self, request: Request) -> Any:
        query = CustomerReportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = ReportSelector.get_customer_report(**query.validated_data)
        header, rows = exports.customer_report_csv(data)
        return build_csv_response("bao_cao_khach_hang.csv", header, rows)


class CustomerInsightView(APIView):
    """GET /api/v1/reports/customers/insights/"""

    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = REPORT_VIEW_PERMISSION

    def get(self, request: Request) -> Any:
        query = CustomerReportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = ReportSelector.get_customer_report(**query.validated_data)
        insight = ReportInsightService.generate(
            ReportType.CUSTOMER, data, query.validated_data
        )
        return success_response(data=insight)
