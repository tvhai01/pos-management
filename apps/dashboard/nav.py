"""
Canonical directory of feature modules for the Dashboard UI.

Single source of truth for "which modules exist and what permission do
they need" — reused by the persistent top navigation (every page, via
`context_processors.nav_modules`) and by the home page's descriptive
module cards (`views.index`), so the permission-gated module list is
never duplicated.
"""

NAV_MODULES: tuple[dict[str, str], ...] = (
    {
        "key": "customer",
        "name": "Khách hàng",
        "description": "Tạo, cập nhật, tìm kiếm, xoá mềm khách hàng.",
        "url_name": "dashboard:customer-list",
        "resource": "customer",
    },
    {
        "key": "product",
        "name": "Sản phẩm",
        "description": "Quản lý sản phẩm, danh mục, giá và trạng thái kinh doanh.",
        "url_name": "dashboard:product-list",
        "resource": "product",
    },
    {
        "key": "inventory",
        "name": "Kho hàng",
        "description": "Theo dõi tồn, nhập, xuất và điều chỉnh số lượng.",
        "url_name": "dashboard:inventory-list",
        "resource": "inventory",
    },
    {
        "key": "order",
        "name": "Đơn hàng",
        "description": "Chọn sản phẩm hiện có, tạo đơn và theo dõi thanh toán.",
        "url_name": "dashboard:order-list",
        "resource": "order",
    },
    {
        "key": "invoice",
        "name": "Hóa đơn và thanh toán",
        "description": "Theo dõi hóa đơn, QR payment và lịch sử giao dịch.",
        "url_name": "dashboard:invoice-list",
        "resource": "invoice",
    },
    {
        "key": "user",
        "name": "Nhân viên",
        "description": "Tạo tài khoản nhân viên và gán vai trò (role).",
        "url_name": "dashboard:staff-list",
        "resource": "user",
    },
    {
        "key": "report",
        "name": "Báo cáo",
        "description": "Doanh thu, sản phẩm bán chạy, tồn kho, thanh toán, khách hàng.",
        "url_name": "dashboard:report-dashboard",
        "resource": "report",
    },
)
