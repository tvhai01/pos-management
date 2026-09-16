"""URL configuration for the session-authenticated Dashboard UI."""

from django.urls import path

from apps.dashboard import views

app_name: str = "dashboard"

urlpatterns: list = [
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("customers/", views.customer_list, name="customer-list"),
    path("customers/create/", views.customer_create, name="customer-create"),
    path(
        "customers/<uuid:customer_id>/edit/",
        views.customer_edit,
        name="customer-edit",
    ),
    path(
        "customers/<uuid:customer_id>/delete/",
        views.customer_delete,
        name="customer-delete",
    ),
    path("staff/", views.staff_list, name="staff-list"),
    path("staff/create/", views.staff_create, name="staff-create"),
    path("staff/<uuid:user_id>/edit/", views.staff_edit, name="staff-edit"),
    path(
        "staff/<uuid:user_id>/deactivate/",
        views.staff_deactivate,
        name="staff-deactivate",
    ),
    path(
        "staff/<uuid:user_id>/activate/",
        views.staff_activate,
        name="staff-activate",
    ),
    path("staff/roles/", views.role_list, name="role-list"),
    path("staff/roles/create/", views.role_create, name="role-create"),
    path("staff/roles/<uuid:role_id>/edit/", views.role_edit, name="role-edit"),
    path("products/", views.product_list, name="product-list"),
    path("products/create/", views.product_create, name="product-create"),
    path(
        "products/<uuid:product_id>/update/",
        views.product_update,
        name="product-update",
    ),
    path(
        "products/<uuid:product_id>/delete/",
        views.product_delete,
        name="product-delete",
    ),
    path(
        "products/<uuid:product_id>/restore/",
        views.product_restore,
        name="product-restore",
    ),
    path("categories/", views.category_list, name="category-list"),
    path("categories/create/", views.category_create, name="category-create"),
    path(
        "categories/<uuid:category_id>/update/",
        views.category_update,
        name="category-update",
    ),
    path(
        "categories/<uuid:category_id>/delete/",
        views.category_delete,
        name="category-delete",
    ),
    path(
        "categories/<uuid:category_id>/restore/",
        views.category_restore,
        name="category-restore",
    ),
    path("trash/", views.trash, name="trash"),
    path("inventory/", views.inventory_list, name="inventory-list"),
    path("invoices/", views.invoice_list, name="invoice-list"),
    path("orders/", views.order_list, name="order-list"),
    path("orders/create/", views.order_create, name="order-create"),
    path("orders/<uuid:order_id>/", views.order_detail, name="order-detail"),
    path(
        "orders/customers/search/",
        views.customer_search,
        name="order-customer-search",
    ),
    path(
        "orders/products/search/",
        views.product_search,
        name="order-product-search",
    ),
    path("invoices/<uuid:invoice_id>/", views.invoice_detail, name="invoice-detail"),
    path(
        "invoices/<uuid:invoice_id>/pending/",
        views.invoice_pending,
        name="invoice-pending",
    ),
    path(
        "invoices/<uuid:invoice_id>/return/",
        views.invoice_return,
        name="invoice-return",
    ),
    path(
        "payments/<uuid:payment_id>/status/",
        views.payment_status,
        name="payment-status",
    ),
    path("invoices/<uuid:invoice_id>/qr/", views.invoice_qr, name="invoice-qr"),
    path(
        "invoices/<uuid:invoice_id>/sepay/",
        views.invoice_sepay,
        name="invoice-sepay",
    ),
    path(
        "invoices/<uuid:invoice_id>/manual/",
        views.invoice_manual,
        name="invoice-manual",
    ),
    path(
        "payments/<uuid:payment_id>/cancel/",
        views.payment_cancel,
        name="payment-cancel",
    ),
    path(
        "inventory/<uuid:product_id>/",
        views.inventory_detail,
        name="inventory-detail",
    ),
    path(
        "inventory/<uuid:product_id>/movement/",
        views.inventory_movement,
        name="inventory-movement",
    ),
    path(
        "inventory/<uuid:product_id>/threshold/",
        views.inventory_threshold,
        name="inventory-threshold",
    ),
    path("reports/", views.report_dashboard, name="report-dashboard"),
    path(
        "reports/revenue/fragment/",
        views.report_revenue_fragment,
        name="report-revenue-fragment",
    ),
    path(
        "reports/products/top-selling/fragment/",
        views.report_top_selling_fragment,
        name="report-top-selling-fragment",
    ),
    path(
        "reports/inventory/fragment/",
        views.report_inventory_fragment,
        name="report-inventory-fragment",
    ),
    path(
        "reports/payments/breakdown/fragment/",
        views.report_payment_breakdown_fragment,
        name="report-payment-breakdown-fragment",
    ),
    path(
        "reports/customers/fragment/",
        views.report_customers_fragment,
        name="report-customers-fragment",
    ),
    path(
        "reports/revenue/export/",
        views.report_revenue_export,
        name="report-revenue-export",
    ),
    path(
        "reports/revenue/insights/",
        views.report_revenue_insights,
        name="report-revenue-insights",
    ),
    path(
        "reports/products/top-selling/export/",
        views.report_top_selling_export,
        name="report-top-selling-export",
    ),
    path(
        "reports/products/top-selling/insights/",
        views.report_top_selling_insights,
        name="report-top-selling-insights",
    ),
    path(
        "reports/inventory/export/",
        views.report_inventory_export,
        name="report-inventory-export",
    ),
    path(
        "reports/inventory/insights/",
        views.report_inventory_insights,
        name="report-inventory-insights",
    ),
    path(
        "reports/payments/breakdown/export/",
        views.report_payment_breakdown_export,
        name="report-payment-breakdown-export",
    ),
    path(
        "reports/payments/breakdown/insights/",
        views.report_payment_breakdown_insights,
        name="report-payment-breakdown-insights",
    ),
    path(
        "reports/customers/export/",
        views.report_customers_export,
        name="report-customers-export",
    ),
    path(
        "reports/customers/insights/",
        views.report_customers_insights,
        name="report-customers-insights",
    ),
]
