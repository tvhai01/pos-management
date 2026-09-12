"""Tests for ReportSelector aggregate queries.

Order/Invoice/Payment fixtures here are built directly via the ORM instead
of `OrderService.create_order` / `PaymentService.create_manual_payment`.
`OrderService.create_order` currently cannot insert ANY Order against
PostgreSQL — it INSERTs the row with `total_amount=0` before the real total
is computed, which violates the `order_total_positive` CheckConstraint on
every call (reproduced with `apps/orders/tests/test_order_flow.py` too, so
it is a pre-existing bug unrelated to Report — reported separately, not
fixed here). These tests only need the resulting rows, not that write path.
"""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.inventory.constants import StockMovementType
from apps.inventory.services import InventoryService
from apps.invoices.constants import InvoiceStatus
from apps.invoices.models import Invoice
from apps.orders.constants import OrderStatus
from apps.orders.models import Order, OrderItem
from apps.payments.constants import (
    PaymentMethod,
    PaymentStatus,
    Provider,
    TransactionType,
)
from apps.payments.models import Payment, PaymentTransaction
from apps.product.constants import ProductStatus, ProductUnit
from apps.product.models import Category, Product
from apps.product.services import ProductService
from apps.reports.constants import RevenueGranularity, TopSellingSortBy
from apps.reports.selectors import ReportSelector


def _create_customer(code: str, user: User) -> Customer:
    return Customer.objects.create(
        customer_code=code,
        full_name=f"Customer {code}",
        phone=f"09{code[-8:].zfill(8)}",
        created_by=user,
        updated_by=user,
    )


def _create_product(sku: str, price: Decimal, user: User) -> Product:
    category = Category.objects.create(
        name=f"Category {sku}", created_by=user, updated_by=user
    )
    return ProductService.create_product(
        sku=sku,
        name=f"Product {sku}",
        cost_price=Decimal("1"),
        selling_price=price,
        category_id=category.id,
        unit=ProductUnit.PIECE,
        status=ProductStatus.ACTIVE,
        created_by=user,
    )


def _create_paid_order(
    customer: Customer,
    items: list[tuple[Product, Decimal]],
    user: User,
    *,
    paid_at=None,
    payment_method: str = PaymentMethod.MANUAL,
    provider: str = Provider.MANUAL,
) -> tuple[Order, Invoice, Payment]:
    """Build a fully Paid Order + Invoice + Payment + PaymentTransaction."""
    paid_at = paid_at or timezone.now()
    subtotal = sum(
        (product.selling_price * qty for product, qty in items), Decimal("0")
    )

    order = Order.objects.create(
        order_number=f"ORD-TEST-{uuid.uuid4().hex[:10].upper()}",
        customer=customer,
        subtotal=subtotal,
        total_amount=subtotal,
        status=OrderStatus.PAID,
        paid_at=paid_at,
        created_by=user,
        updated_by=user,
    )
    for product, qty in items:
        line_total = product.selling_price * qty
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            product_sku=product.sku,
            unit_price=product.selling_price,
            quantity=qty,
            subtotal=line_total,
            total_amount=line_total,
            created_by=user,
            updated_by=user,
        )

    invoice = Invoice.objects.create(
        invoice_number=f"INV-TEST-{uuid.uuid4().hex[:10].upper()}",
        customer=customer,
        order=order,
        subtotal=subtotal,
        total_amount=subtotal,
        status=InvoiceStatus.PAID,
        paid_at=paid_at,
        created_by=user,
        updated_by=user,
    )

    payment = Payment.objects.create(
        invoice=invoice,
        reference=f"PAY-TEST-{uuid.uuid4().hex[:10].upper()}",
        amount=subtotal,
        payment_method=payment_method,
        status=PaymentStatus.SUCCESS,
        processed_at=paid_at,
        created_by=user,
        updated_by=user,
    )
    PaymentTransaction.objects.create(
        payment=payment,
        invoice=invoice,
        provider=provider,
        transaction_type=TransactionType.PAYMENT,
        amount=subtotal,
        status=PaymentStatus.SUCCESS,
        payment_method=payment_method,
        processed_at=paid_at,
        created_by=user,
        updated_by=user,
    )
    return order, invoice, payment


def _create_unpaid_invoice(customer: Customer, amount: Decimal, user: User) -> Invoice:
    """A Pending-payment Invoice — must never count as revenue."""
    return Invoice.objects.create(
        invoice_number=f"INV-TEST-{uuid.uuid4().hex[:10].upper()}",
        customer=customer,
        subtotal=amount,
        total_amount=amount,
        status=InvoiceStatus.PENDING_PAYMENT,
        created_by=user,
        updated_by=user,
    )


@pytest.mark.django_db
class TestRevenueReport:
    def test_only_counts_paid_invoices(self, create_user):
        customer = _create_customer("CUS0000001", create_user)
        product = _create_product("SKU-REV-001", Decimal("100"), create_user)
        today = timezone.localdate()

        _create_paid_order(customer, [(product, Decimal("2"))], create_user)
        _create_unpaid_invoice(customer, Decimal("500"), create_user)

        data = ReportSelector.get_revenue_report(today, today)

        assert data["total_revenue"] == Decimal("200")
        assert data["invoice_count"] == 1
        assert data["average_invoice_value"] == Decimal("200")

    def test_average_is_zero_when_no_paid_invoices(self):
        today = timezone.localdate()
        data = ReportSelector.get_revenue_report(today, today)
        assert data["total_revenue"] == Decimal("0")
        assert data["invoice_count"] == 0
        assert data["average_invoice_value"] == Decimal("0")

    def test_excludes_invoices_outside_date_range(self, create_user):
        customer = _create_customer("CUS0000011", create_user)
        product = _create_product("SKU-REV-002", Decimal("100"), create_user)
        today = timezone.localdate()
        _create_paid_order(
            customer,
            [(product, Decimal("1"))],
            create_user,
            paid_at=timezone.now() - timedelta(days=10),
        )

        data = ReportSelector.get_revenue_report(today, today)
        assert data["total_revenue"] == Decimal("0")

    def test_granularity_is_day_for_short_range(self):
        today = timezone.localdate()
        data = ReportSelector.get_revenue_report(today - timedelta(days=5), today)
        assert data["granularity"] == RevenueGranularity.DAY

    def test_granularity_is_week_for_medium_range(self):
        today = timezone.localdate()
        data = ReportSelector.get_revenue_report(today - timedelta(days=60), today)
        assert data["granularity"] == RevenueGranularity.WEEK

    def test_granularity_is_month_for_long_range(self):
        today = timezone.localdate()
        data = ReportSelector.get_revenue_report(today - timedelta(days=400), today)
        assert data["granularity"] == RevenueGranularity.MONTH


@pytest.mark.django_db
class TestTopSellingProducts:
    def test_sort_by_revenue_vs_quantity_differ(self, create_user):
        customer = _create_customer("CUS0000002", create_user)
        # Product A: 1 unit at 100 -> revenue 100, quantity 1.
        product_a = _create_product("SKU-TOP-A", Decimal("100"), create_user)
        # Product B: 5 units at 15 -> revenue 75, quantity 5.
        product_b = _create_product("SKU-TOP-B", Decimal("15"), create_user)
        _create_paid_order(customer, [(product_a, Decimal("1"))], create_user)
        _create_paid_order(customer, [(product_b, Decimal("5"))], create_user)
        today = timezone.localdate()

        by_revenue = ReportSelector.get_top_selling_products(
            today, today, 10, TopSellingSortBy.REVENUE
        )
        by_quantity = ReportSelector.get_top_selling_products(
            today, today, 10, TopSellingSortBy.QUANTITY
        )

        assert by_revenue[0]["product_sku"] == "SKU-TOP-A"
        assert by_quantity[0]["product_sku"] == "SKU-TOP-B"

    def test_top_n_limits_result_count(self, create_user):
        customer = _create_customer("CUS0000003", create_user)
        for i in range(3):
            product = _create_product(f"SKU-LIM-{i}", Decimal("10"), create_user)
            _create_paid_order(customer, [(product, Decimal("1"))], create_user)
        today = timezone.localdate()

        rows = ReportSelector.get_top_selling_products(
            today, today, 2, TopSellingSortBy.REVENUE
        )
        assert len(rows) == 2

    def test_deleted_product_still_shows_snapshot_name(self, create_user):
        customer = _create_customer("CUS0000004", create_user)
        product = _create_product("SKU-SNAP-1", Decimal("10"), create_user)
        _create_paid_order(customer, [(product, Decimal("1"))], create_user)
        ProductService.delete_product(product.id, deleted_by=create_user)
        today = timezone.localdate()

        rows = ReportSelector.get_top_selling_products(
            today, today, 10, TopSellingSortBy.REVENUE
        )
        assert rows[0]["product_sku"] == "SKU-SNAP-1"


@pytest.mark.django_db
class TestInventoryReport:
    def test_counts_low_and_out_of_stock(self, create_user):
        out_of_stock_product = _create_product(
            "SKU-INV-OUT", Decimal("10"), create_user
        )
        low_stock_product = _create_product("SKU-INV-LOW", Decimal("10"), create_user)
        in_stock_product = _create_product("SKU-INV-OK", Decimal("10"), create_user)

        InventoryService.initialize_inventory(out_of_stock_product)
        InventoryService.initialize_inventory(low_stock_product)
        InventoryService.initialize_inventory(in_stock_product)

        InventoryService.record_movement(
            product_id=low_stock_product.id,
            movement_type=StockMovementType.INBOUND,
            quantity=Decimal("5"),
            created_by=create_user,
        )
        InventoryService.record_movement(
            product_id=in_stock_product.id,
            movement_type=StockMovementType.INBOUND,
            quantity=Decimal("50"),
            created_by=create_user,
        )
        today = timezone.localdate()

        data = ReportSelector.get_inventory_report(today, today)

        assert data["out_of_stock_count"] == 1
        assert data["low_stock_count"] == 1
        assert data["inbound_total"] == Decimal("55")
        skus = {row["product__sku"] for row in data["out_of_stock_products"]}
        assert "SKU-INV-OUT" in skus

    def test_excludes_soft_deleted_products_from_value(self, create_user):
        product = _create_product("SKU-INV-DEL", Decimal("10"), create_user)
        InventoryService.initialize_inventory(product)
        InventoryService.record_movement(
            product_id=product.id,
            movement_type=StockMovementType.INBOUND,
            quantity=Decimal("10"),
            created_by=create_user,
        )
        ProductService.delete_product(product.id, deleted_by=create_user)
        today = timezone.localdate()

        data = ReportSelector.get_inventory_report(today, today)
        assert data["inventory_value"] == Decimal("0")


@pytest.mark.django_db
class TestPaymentBreakdown:
    def test_groups_success_amount_by_method(self, create_user):
        customer = _create_customer("CUS0000005", create_user)
        product = _create_product("SKU-PAY-1", Decimal("100"), create_user)
        _create_paid_order(customer, [(product, Decimal("1"))], create_user)
        today = timezone.localdate()

        data = ReportSelector.get_payment_breakdown(today, today)

        method_row = next(
            row
            for row in data["by_payment_method"]
            if row["key"] == PaymentMethod.MANUAL
        )
        assert method_row["success_amount"] == Decimal("100")
        assert method_row["total_count"] == 1

        provider_row = next(
            row for row in data["by_provider"] if row["key"] == Provider.MANUAL
        )
        assert provider_row["success_amount"] == Decimal("100")

    def test_failed_transactions_excluded_from_success_amount(self, create_user):
        customer = _create_customer("CUS0000012", create_user)
        product = _create_product("SKU-PAY-2", Decimal("100"), create_user)
        _order, invoice, payment = _create_paid_order(
            customer, [(product, Decimal("1"))], create_user
        )
        PaymentTransaction.objects.create(
            payment=payment,
            invoice=invoice,
            provider=Provider.SEPAY,
            transaction_type=TransactionType.PAYMENT,
            amount=Decimal("50"),
            status=PaymentStatus.FAILED,
            payment_method=PaymentMethod.QR,
            processed_at=timezone.now(),
            created_by=create_user,
            updated_by=create_user,
        )
        today = timezone.localdate()

        data = ReportSelector.get_payment_breakdown(today, today)
        qr_row = next(
            row for row in data["by_payment_method"] if row["key"] == PaymentMethod.QR
        )
        assert qr_row["success_amount"] == Decimal("0")
        assert qr_row["total_count"] == 1


@pytest.mark.django_db
class TestCustomerReport:
    def test_top_customers_ordered_by_total_spent(self, create_user):
        big_spender = _create_customer("CUS0000006", create_user)
        small_spender = _create_customer("CUS0000007", create_user)
        product = _create_product("SKU-CUST-1", Decimal("100"), create_user)
        _create_paid_order(big_spender, [(product, Decimal("3"))], create_user)
        _create_paid_order(small_spender, [(product, Decimal("1"))], create_user)
        today = timezone.localdate()

        data = ReportSelector.get_customer_report(today, today, 10)

        assert data["top_customers"][0]["customer__customer_code"] == "CUS0000006"
        assert data["top_customers"][0]["total_spent"] == Decimal("300")

    def test_soft_deleted_customer_still_counted_in_top_spenders(self, create_user):
        customer = _create_customer("CUS0000008", create_user)
        product = _create_product("SKU-CUST-2", Decimal("50"), create_user)
        _create_paid_order(customer, [(product, Decimal("1"))], create_user)
        customer.is_deleted = True
        customer.save(update_fields=["is_deleted"])
        today = timezone.localdate()

        data = ReportSelector.get_customer_report(today, today, 10)
        assert any(
            row["customer__customer_code"] == "CUS0000008"
            for row in data["top_customers"]
        )

    def test_new_customers_count_uses_created_at_range(self, create_user):
        _create_customer("CUS0000009", create_user)
        old = _create_customer("CUS0000010", create_user)
        Customer.objects.filter(id=old.id).update(
            created_at=timezone.now() - timedelta(days=90)
        )
        today = timezone.localdate()

        data = ReportSelector.get_customer_report(today - timedelta(days=1), today, 10)
        assert data["new_customers_count"] == 1
