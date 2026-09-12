"""
Management command: seed_demo_data.

Populates the database with a realistic set of demo data for local
development and manual testing: the permission catalog, a handful of
staff roles matching real POS positions, ~15 staff accounts distributed
across those roles, and ~100 customer records.

Idempotent by design — every write is a `get_or_create`/existence check
keyed on a unique field, so re-running it (e.g. on every
`docker compose up --build`) never duplicates rows. Refuses to run
unless `settings.DEBUG` is True, so it can never seed fake data into a
production database even if invoked there by mistake.
"""

from datetime import date
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

DEFAULT_STAFF_PASSWORD: str = (
    "12345678@"  # noqa: S105 — documented demo default, not a secret
)
CUSTOMER_COUNT: int = 100

# Matches the dev account documented in README.md § Quick Start.
DEV_SUPERUSER_EMAIL: str = "admin@pos.com"
DEV_SUPERUSER_PASSWORD: str = "PosDev@2026!"  # noqa: S105 — documented dev default

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

        self._seed_dev_superuser()
        self._seed_permissions()
        roles = self._seed_roles()
        self._seed_staff(roles, faker)
        self._seed_customers(faker)

        self.stdout.write(self.style.SUCCESS("Demo data seeding complete."))

    def _seed_dev_superuser(self) -> None:
        """Ensure the README's documented dev superuser account exists."""
        if User.objects.filter(email=DEV_SUPERUSER_EMAIL).exists():
            self.stdout.write("Superuser: already exists.")
            return
        User.objects.create_superuser(
            email=DEV_SUPERUSER_EMAIL,
            password=DEV_SUPERUSER_PASSWORD,
            full_name="Admin",
        )
        self.stdout.write(f"Superuser: created ({DEV_SUPERUSER_EMAIL}).")

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
