"""
Project-level views (not owned by any single app).

Home / API root — a self-descriptive directory of every feature module,
so hitting `/` gives a real overview instead of redirecting straight into
one module's endpoint (health check).
"""

from typing import Any

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from shared.response import success_response

# Directory of feature modules. Extend this dict whenever a new app ships
# (see docs/prompt-features.md step "Cập nhật README" — the same entry also
# belongs in the README API table).
FEATURE_MODULES: dict[str, dict[str, str]] = {
    "health": {
        "name": "Health Check",
        "base_url": "/api/v1/health/",
        "description": "Kiểm tra tình trạng hoạt động của dịch vụ (DB, Redis).",
    },
    "auth": {
        "name": "Authentication",
        "base_url": "/api/v1/auth/",
        "description": "Đăng nhập/đăng xuất JWT, làm mới token, hồ sơ cá nhân.",
    },
    "rbac": {
        "name": "RBAC — Roles & Permissions",
        "base_url": "/api/v1/roles/",
        "description": "Quản lý vai trò (Role) và phân quyền (Permission).",
    },
    "customers": {
        "name": "Customer Management",
        "base_url": "/api/v1/customers/",
        "description": "Quản lý khách hàng: tạo, cập nhật, tìm kiếm, xoá mềm.",
    },
    "products": {
        "name": "Product Management",
        "base_url": "/api/v1/products/",
        "description": "Quản lý sản phẩm, danh mục, giá bán và vòng đời sản phẩm.",
    },
    "inventory": {
        "name": "Inventory Management",
        "base_url": "/api/v1/inventory/",
        "description": "Quản lý tồn hiện tại và lịch sử nhập, xuất, điều chỉnh kho.",
    },
    "admin": {
        "name": "Django Admin",
        "base_url": "/admin/",
        "description": "Trang quản trị dữ liệu trực tiếp (Django Admin site).",
    },
}


class HomeView(APIView):
    """API root — landing page listing all available feature modules.

    GET /
    """

    permission_classes = (AllowAny,)
    authentication_classes: tuple = ()

    def get(self, request: Request) -> Any:
        """Return the service directory: name, version, and feature modules.

        Returns:
            Standardized success response with the module directory.
        """
        return success_response(
            data={
                "service": "POS Management System",
                "version": settings.APP_VERSION,
                "modules": FEATURE_MODULES,
            },
            message="Chào mừng đến với POS Management System API.",
        )
