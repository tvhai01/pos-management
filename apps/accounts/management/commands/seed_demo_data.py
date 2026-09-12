"""
Management command: seed_demo_data.

Populates the database with a realistic set of demo data for local
development and manual testing: the permission catalog, a handful of
staff roles matching real POS positions, ~15 staff accounts distributed
across those roles, ~100 customer records, ~10 product categories with
~100 products spread across them, and an initial warehouse stock-in
movement per product spread across ten different quantity levels.

Idempotent by design — every write is a `get_or_create`/existence check
keyed on a unique field, so re-running it (e.g. on every
`docker compose up --build`) never duplicates rows. Refuses to run
unless `settings.DEBUG` is True, so it can never seed fake data into a
production database even if invoked there by mistake.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from faker import Faker

from apps.accounts.constants import PermissionAction, PermissionResource
from apps.accounts.models import Permission, Role, User
from apps.accounts.services import UserService
from apps.customers.constants import CustomerGender, CustomerStatus
from apps.customers.selectors import CustomerSelector
from apps.customers.services import CustomerService
from apps.inventory.constants import StockMovementType
from apps.inventory.services import InventoryService
from apps.product.constants import ProductStatus, ProductUnit
from apps.product.selectors import CategorySelector, ProductSelector
from apps.product.services import CategoryService, ProductService

DEFAULT_STAFF_PASSWORD: str = (
    "12345678@"  # noqa: S105 — documented demo default, not a secret
)
CUSTOMER_COUNT: int = 100

# Matches the dev account documented in README.md § Quick Start.
DEV_SUPERUSER_EMAIL: str = "admin@pos.com"
DEV_SUPERUSER_PASSWORD: str = "PosDev@2026!"  # noqa: S105 — documented dev default

# 10 categories x 10 products = ~100 products, one representative unit of
# measure per category so the demo catalogue exercises a good spread of
# ProductUnit values.
CATEGORY_PRODUCTS: dict[str, tuple[str, list[str]]] = {
    "Đồ uống": (
        ProductUnit.BOTTLE,
        [
            "Coca-Cola 330ml",
            "Pepsi 330ml",
            "Nước suối Aquafina 500ml",
            "Trà xanh Không Độ 500ml",
            "Nước cam Twister 1L",
            "Bia Tiger lon 330ml",
            "Bia Heineken lon 330ml",
            "Sting dâu 330ml",
            "Nước tăng lực Redbull 250ml",
            "Trà atiso Tân Hiệp Phát 500ml",
        ],
    ),
    "Bánh kẹo": (
        ProductUnit.PACK,
        [
            "Bánh Oreo",
            "Kẹo Alpenliebe",
            "Snack Oishi",
            "Bánh Chocopie",
            "Kẹo Mentos",
            "Bánh quy Cosy",
            "Kẹo cao su Doublemint",
            "Bánh AFC",
            "Snack Lay's",
            "Kẹo dẻo Haribo",
        ],
    ),
    "Thực phẩm khô": (
        ProductUnit.PACK,
        [
            "Mì Hảo Hảo",
            "Mì Omachi",
            "Gạo ST25 5kg",
            "Miến Phú Hương",
            "Cháo ăn liền Vifon",
            "Phở ăn liền Vifon",
            "Bún khô",
            "Mì Kokomi",
            "Cơm cháy",
            "Miến dong",
        ],
    ),
    "Gia vị": (
        ProductUnit.BOTTLE,
        [
            "Nước mắm Nam Ngư",
            "Nước tương Chinsu",
            "Muối i-ốt",
            "Đường trắng",
            "Bột ngọt Ajinomoto",
            "Tương ớt Chinsu",
            "Dầu ăn Neptune",
            "Hạt nêm Knorr",
            "Tiêu xay",
            "Sa tế",
        ],
    ),
    "Sữa và chế phẩm": (
        ProductUnit.BOX,
        [
            "Sữa tươi Vinamilk",
            "Sữa đặc Ông Thọ",
            "Sữa chua Vinamilk",
            "Phô mai con bò cười",
            "Sữa bột Dielac",
            "Bơ lạt",
            "Sữa hạt Nutifood",
            "Whipping cream",
            "Sữa chua uống Yakult",
            "Kem Wall's",
        ],
    ),
    "Đồ gia dụng": (
        ProductUnit.BOTTLE,
        [
            "Nước rửa chén Sunlight",
            "Bột giặt Omo",
            "Nước lau sàn Gift",
            "Túi rác",
            "Khăn giấy Pulppy",
            "Nước xả vải Comfort",
            "Bàn chải đánh răng",
            "Kem đánh răng P/S",
            "Xà phòng Lifebuoy",
            "Nước rửa tay",
        ],
    ),
    "Văn phòng phẩm": (
        ProductUnit.PIECE,
        [
            "Bút bi Thiên Long",
            "Vở học sinh Campus",
            "Bút chì 2B",
            "Thước kẻ 30cm",
            "Gôm tẩy",
            "Sổ tay A5",
            "Kẹp giấy",
            "Băng keo trong",
            "Bút highlight",
            "Bìa hồ sơ",
        ],
    ),
    "Mỹ phẩm": (
        ProductUnit.PIECE,
        [
            "Sữa rửa mặt Simple",
            "Kem chống nắng Anessa",
            "Son Romand",
            "Nước hoa hồng",
            "Mặt nạ giấy",
            "Kem dưỡng ẩm",
            "Phấn phủ",
            "Chì kẻ mày",
            "Sữa dưỡng thể",
            "Dầu gội Clear",
        ],
    ),
    "Vệ sinh cá nhân": (
        ProductUnit.PACK,
        [
            "Băng vệ sinh Diana",
            "Tã Bobby",
            "Khăn ướt Mamamy",
            "Dao cạo râu Gillette",
            "Bàn chải Colgate",
            "Nước súc miệng Listerine",
            "Khẩu trang y tế",
            "Giấy vệ sinh Pulppy",
            "Xịt khử mùi Nivea",
            "Bông tẩy trang",
        ],
    ),
    "Đồ chơi": (
        ProductUnit.PIECE,
        [
            "Lego mini",
            "Xe ô tô đồ chơi",
            "Búp bê Barbie",
            "Bóng bay",
            "Bộ xếp hình",
            "Đất nặn",
            "Rubik",
            "Súng nước đồ chơi",
            "Diều giấy",
            "Con quay",
        ],
    ),
}

# Ten warehouse quantity levels, cycled across every seeded product so the
# initial stock is spread evenly from near-empty to well-stocked instead of
# every product landing on the same balance.
STOCK_LEVELS: tuple[int, ...] = (3, 8, 15, 25, 40, 60, 90, 120, 200, 350)

# Only the action/resource combinations actually enforced somewhere in the
# app (matches every `require_permission`/`required_permission` call site
# plus the dict constants declared in each app's `permissions.py`).
PERMISSION_CATALOG: dict[str, list[str]] = {
    PermissionResource.ROLE: [
        PermissionAction.VIEW,
        PermissionAction.CREATE,
        PermissionAction.UPDATE,
        PermissionAction.DELETE,
    ],
    PermissionResource.USER: [
        PermissionAction.VIEW,
        PermissionAction.CREATE,
        PermissionAction.UPDATE,
        PermissionAction.DELETE,
    ],
    PermissionResource.CUSTOMER: [
        PermissionAction.VIEW,
        PermissionAction.CREATE,
        PermissionAction.UPDATE,
        PermissionAction.DELETE,
        PermissionAction.EXPORT,
    ],
    PermissionResource.PRODUCT: [
        PermissionAction.VIEW,
        PermissionAction.CREATE,
        PermissionAction.UPDATE,
        PermissionAction.DELETE,
    ],
    PermissionResource.CATEGORY: [
        PermissionAction.VIEW,
        PermissionAction.CREATE,
        PermissionAction.UPDATE,
        PermissionAction.DELETE,
    ],
    PermissionResource.INVENTORY: [
        PermissionAction.VIEW,
        PermissionAction.CREATE,
        PermissionAction.UPDATE,
    ],
    PermissionResource.INVOICE: [
        PermissionAction.VIEW,
        PermissionAction.CREATE,
        PermissionAction.UPDATE,
    ],
    PermissionResource.ORDER: [
        PermissionAction.VIEW,
        PermissionAction.CREATE,
        PermissionAction.UPDATE,
    ],
    PermissionResource.PAYMENT: [
        PermissionAction.CREATE,
        PermissionAction.UPDATE,
        PermissionAction.APPROVE,
    ],
}

# Position (→ Role) to the permissions it grants. Store managers get every
# business permission plus read-only visibility into staff/roles; the other
# positions get only what their day-to-day screens require.
_ALL_BUSINESS_PERMISSIONS: list[tuple[str, str]] = [
    (action, resource)
    for resource, actions in PERMISSION_CATALOG.items()
    for action in actions
    if resource not in {PermissionResource.ROLE, PermissionResource.USER}
]

POSITION_PERMISSIONS: dict[str, list[tuple[str, str]]] = {
    "Quản lý cửa hàng": [
        *_ALL_BUSINESS_PERMISSIONS,
        (PermissionAction.VIEW, PermissionResource.USER),
        (PermissionAction.VIEW, PermissionResource.ROLE),
    ],
    "Thu ngân": [
        (PermissionAction.VIEW, PermissionResource.CUSTOMER),
        (PermissionAction.CREATE, PermissionResource.CUSTOMER),
        (PermissionAction.VIEW, PermissionResource.PRODUCT),
        (PermissionAction.VIEW, PermissionResource.ORDER),
        (PermissionAction.CREATE, PermissionResource.ORDER),
        (PermissionAction.VIEW, PermissionResource.INVOICE),
        (PermissionAction.CREATE, PermissionResource.PAYMENT),
    ],
    "Nhân viên kho": [
        (PermissionAction.VIEW, PermissionResource.INVENTORY),
        (PermissionAction.CREATE, PermissionResource.INVENTORY),
        (PermissionAction.UPDATE, PermissionResource.INVENTORY),
        (PermissionAction.VIEW, PermissionResource.PRODUCT),
        (PermissionAction.UPDATE, PermissionResource.PRODUCT),
        (PermissionAction.VIEW, PermissionResource.CATEGORY),
    ],
    "Nhân viên bán hàng": [
        (PermissionAction.VIEW, PermissionResource.CUSTOMER),
        (PermissionAction.CREATE, PermissionResource.CUSTOMER),
        (PermissionAction.VIEW, PermissionResource.PRODUCT),
        (PermissionAction.VIEW, PermissionResource.INVENTORY),
        (PermissionAction.VIEW, PermissionResource.ORDER),
        (PermissionAction.CREATE, PermissionResource.ORDER),
    ],
}

# How many of the 15 demo staff accounts hold each position.
STAFF_DISTRIBUTION: dict[str, int] = {
    "Quản lý cửa hàng": 2,
    "Thu ngân": 4,
    "Nhân viên kho": 4,
    "Nhân viên bán hàng": 5,
}


class Command(BaseCommand):
    """Seed demo roles, staff accounts, and customers for local testing."""

    help = (
        "Seed ~100 demo customers and ~15 demo staff accounts (with "
        "position-appropriate roles) for local development and manual "
        "testing. Idempotent; refuses to run unless DEBUG=True."
    )

    def handle(self, *args: Any, **options: Any) -> None:
        """Run the full seed sequence: permissions → roles → staff → customers."""
        if not settings.DEBUG:
            raise CommandError(
                "seed_demo_data refuses to run when DEBUG=False "
                "(development/demo environments only)."
            )

        faker = Faker("vi_VN")
        Faker.seed(20260912)

        actor = self._seed_dev_superuser()
        self._seed_permissions()
        roles = self._seed_roles()
        self._seed_staff(roles, faker)
        self._seed_customers(faker)
        self._seed_products(actor)

        self.stdout.write(self.style.SUCCESS("Demo data seeding complete."))

    def _seed_dev_superuser(self) -> User:
        """Ensure the README's documented dev superuser account exists."""
        existing = User.objects.filter(email=DEV_SUPERUSER_EMAIL).first()
        if existing is not None:
            self.stdout.write("Superuser: already exists.")
            return existing
        user = User.objects.create_superuser(
            email=DEV_SUPERUSER_EMAIL,
            password=DEV_SUPERUSER_PASSWORD,
            full_name="Admin",
        )
        self.stdout.write(f"Superuser: created ({DEV_SUPERUSER_EMAIL}).")
        return user

    @transaction.atomic
    def _seed_permissions(self) -> None:
        """Ensure the full action/resource permission catalog exists."""
        created = 0
        for resource, actions in PERMISSION_CATALOG.items():
            for action in actions:
                _, was_created = Permission.objects.get_or_create(
                    action=action,
                    resource=resource,
                    defaults={
                        "name": (
                            f"{PermissionAction(action).label} "
                            f"{PermissionResource(resource).label}"
                        )
                    },
                )
                created += int(was_created)
        self.stdout.write(
            f"Permissions: {created} created " f"({Permission.objects.count()} total)."
        )

    def _seed_roles(self) -> dict[str, Role]:
        """Ensure one Role per demo position, synced to its permission set."""
        roles: dict[str, Role] = {}
        for position, pairs in POSITION_PERMISSIONS.items():
            role, _ = Role.objects.get_or_create(
                name=position,
                defaults={"description": f"Vai trò mặc định cho vị trí {position}."},
            )
            query = Q()
            for action, resource in pairs:
                query |= Q(action=action, resource=resource)
            permission_ids = list(
                Permission.objects.filter(query).values_list("id", flat=True)
            )
            role.permissions.set(permission_ids)
            roles[position] = role
        self.stdout.write(f"Roles: {len(roles)} positions ready.")
        return roles

    def _seed_staff(self, roles: dict[str, Role], faker: Faker) -> None:
        """Ensure ~15 staff accounts exist, distributed across positions."""
        created = 0
        index = 1
        for position, count in STAFF_DISTRIBUTION.items():
            role = roles[position]
            for _ in range(count):
                email = f"nhanvien{index:02d}@pos.com"
                if not User.objects.filter(email=email).exists():
                    UserService.create_user(
                        email=email,
                        full_name=faker.name(),
                        password=DEFAULT_STAFF_PASSWORD,
                        phone=f"08{index:08d}",
                        role_ids=[role.id],
                    )
                    created += 1
                index += 1
        self.stdout.write(
            f"Staff: {created} created "
            f"({sum(STAFF_DISTRIBUTION.values())} total, "
            f"password '{DEFAULT_STAFF_PASSWORD}')."
        )

    def _seed_customers(self, faker: Faker) -> None:
        """Ensure ~100 customer records exist."""
        created = 0
        for i in range(1, CUSTOMER_COUNT + 1):
            code = f"CUS{i:04d}"
            if CustomerSelector.code_exists(code):
                continue
            birthday: date = faker.date_of_birth(minimum_age=18, maximum_age=65)
            CustomerService.create_customer(
                customer_code=code,
                full_name=faker.name(),
                phone=f"09{i:08d}",
                email=f"khachhang{i:04d}@example.com",
                gender=faker.random_element(CustomerGender.values),
                birthday=birthday,
                address=faker.address(),
                status=CustomerStatus.ACTIVE,
            )
            created += 1
        self.stdout.write(f"Customers: {created} created ({CUSTOMER_COUNT} total).")

    def _seed_products(self, actor: User) -> None:
        """Ensure ~10 categories and ~100 products (with initial stock) exist."""
        created_categories = 0
        created_products = 0
        index = 1
        for category_name, (unit, product_names) in CATEGORY_PRODUCTS.items():
            if CategorySelector.name_exists(category_name):
                category = CategorySelector.get_all_categories().get(name=category_name)
            else:
                category = CategoryService.create_category(
                    name=category_name,
                    description=f"Danh mục {category_name}.",
                    created_by=actor,
                )
                created_categories += 1

            for product_name in product_names:
                sku = f"SKU{index:04d}"
                if not ProductSelector.sku_exists(sku):
                    cost_price = Decimal(10_000 + (index * 733) % 90_000)
                    selling_price = (cost_price * Decimal("1.3")).quantize(Decimal("1"))
                    product = ProductService.create_product(
                        sku=sku,
                        name=product_name,
                        cost_price=cost_price,
                        selling_price=selling_price,
                        description=f"{product_name} — hàng demo để test hệ thống.",
                        category_id=category.id,
                        unit=unit,
                        status=ProductStatus.ACTIVE,
                        created_by=actor,
                    )
                    InventoryService.record_movement(
                        product_id=product.id,
                        movement_type=StockMovementType.INBOUND,
                        quantity=STOCK_LEVELS[(index - 1) % len(STOCK_LEVELS)],
                        reference_code=f"SEED-{sku}",
                        note="Seed demo data — nhập kho ban đầu.",
                        created_by=actor,
                    )
                    created_products += 1
                index += 1

        self.stdout.write(
            f"Categories: {created_categories} created "
            f"({len(CATEGORY_PRODUCTS)} total)."
        )
        self.stdout.write(
            f"Products: {created_products} created "
            f"({index - 1} total, inventory spread across "
            f"{len(STOCK_LEVELS)} stock levels)."
        )
