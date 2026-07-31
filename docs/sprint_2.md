# Sprint 2 — Customer Management

**Completed:** 2026-07-31

> This sprint is the canonical worked example referenced by
> [`docs/prompt-features.md`](prompt-features.md) — when writing the prompt
> for a future module, cross-check against how each requirement here mapped
> to actual code.

## Summary

Sprint 2 implements the Customer Management module — full CRUD, search,
filtering, sorting, pagination, and RBAC-gated access. This module is the
foundation for Invoice, Order, and Sales modules planned in later sprints.
Authentication, JWT, and RBAC from Sprint 1 were **not modified** — only
reused.

## What Was Built

### Customer Entity

- **Customer model** (`apps/customers/models.py`) — extends `shared.base_model.AuditModel`
  (UUID PK, `created_at`/`updated_at`/`created_by`/`updated_by` for free).
  Fields: `customer_code` (unique), `full_name`, `phone` (unique, format-validated),
  `email`, `gender`, `birthday`, `address`, `note`, `status`.
- **Soft delete** — `is_deleted` / `deleted_at`. The default manager
  (`Customer.objects`) transparently excludes deleted rows; `Customer.all_objects`
  exposes everything (used by the admin site and by uniqueness checks, since the
  DB unique constraints on `customer_code`/`phone` are table-wide).
- **CustomerStatus** TextChoices — `ACTIVE`, `INACTIVE`, `BLOCKED`.
- **CustomerGender** TextChoices — `MALE`, `FEMALE`, `OTHER`.

### Features (5 endpoints)

- **Create** (`POST /api/v1/customers/`) — requires `create:customer`.
- **List / Search / Filter / Sort / Paginate** (`GET /api/v1/customers/`) —
  requires `view:customer`. Query params: `?search=`, `?status=`, `?ordering=`,
  `?page=`, `?page_size=`.
- **Detail** (`GET /api/v1/customers/{id}/`) — requires `view:customer`.
- **Update** (`PUT /api/v1/customers/{id}/`) — requires `update:customer`.
- **Delete — soft** (`DELETE /api/v1/customers/{id}/`) — requires `delete:customer`.

`Customer.Export` (`export:customer`) is declared in RBAC now so a future CSV/Excel
export endpoint doesn't require a migration, but no export endpoint ships this
sprint (not in the Sprint 2 API scope).

### Layers

- **`apps/customers/validators.py`** — `PHONE_REGEX` (9–15 digits, optional
  leading `+`) shared by the model field validator and the serializer.
- **`apps/customers/managers.py`** — `CustomerManager`, the soft-delete-aware
  default manager.
- **`apps/customers/selectors.py`** — `CustomerSelector`: `get_customer_by_id`,
  `get_customer_by_code`, `get_all_customers`, `code_exists`, `phone_exists`
  (both existence checks accept `exclude_id` for update flows and check
  `all_objects` so soft-deleted rows still block a duplicate).
- **`apps/customers/serializers.py`** — `CreateCustomerSerializer`,
  `UpdateCustomerSerializer` (all fields optional, `context["customer_id"]` for
  self-exclusion), `CustomerListSerializer` (lightweight), `CustomerDetailSerializer`
  (full fields + `created_by`/`updated_by` resolved to email).
- **`apps/customers/services.py`** — `CustomerService`: `create_customer`,
  `update_customer`, `delete_customer` (soft). All business logic lives here;
  views never touch the ORM directly.
- **`apps/customers/permissions.py`** — `CUSTOMER_VIEW_PERMISSION` /
  `_CREATE_` / `_UPDATE_` / `_DELETE_` / `_EXPORT_PERMISSION` dict constants.
  RBAC *enforcement* is reused as-is from `apps.accounts.permissions.HasPermission`
  — no new permission class was written.
- **`apps/customers/views.py`** — `CustomerListCreateView`, `CustomerDetailView`,
  both `GenericAPIView` subclasses (not plain `APIView`, unlike Sprint 1's Role
  views) so they get `filter_queryset` / `paginate_queryset` / `get_paginated_response`
  for free instead of reimplementing them.
- **`shared/pagination.py`** — added `paginated_success_response()`, a reusable
  helper that filters + paginates + serializes a queryset and wraps DRF's
  paginated payload in the project's `success_response` envelope. Written once
  here so Product/Order/Invoice list endpoints in later sprints don't
  reimplement pagination plumbing.

### Tests (35 tests, `apps/customers/tests/test_customer.py`)

- Model: creation, `__str__`, unique constraints (`customer_code`, `phone`),
  soft-delete visibility.
- Selector: id/code lookup, `code_exists`/`phone_exists` incl. `exclude_id`.
- Service: create, update (incl. not-found), soft delete (incl. not-found).
- API: create (with/without permission, duplicate code/phone, bad phone format,
  superuser bypass), list (with/without permission, pagination envelope),
  search (code/phone match, no-match), filter by status, detail (found/404),
  update (with/without permission), delete (with/without permission,
  post-delete 404).

### Infrastructure Fix

Discovered and fixed a **pre-existing bug**, not introduced by this sprint:
`tests/conftest.py` fixtures (`api_client`, `create_user`, `staff_role`, …)
were never actually reachable from `apps/accounts/tests/` or any other app's
test package. Pytest only shares a `conftest.py`'s fixtures with tests nested
under its own directory; `tests/` and `apps/` are siblings under the project
root, not parent/child, so every fixture-based test in Sprint 1 was silently
broken (`fixture 'api_client' not found`) whenever run outside of a very
specific invocation. Added a root-level `conftest.py` that re-exports
`tests/conftest.py` (`from tests.conftest import *`) so fixtures are visible
project-wide. Verified: all 88 tests (53 pre-existing + 35 new) now pass.

## Design Decisions

| Decision | Rationale |
|---|---|
| `PUT` on detail endpoint, but fields optional | Spec asked for `PUT`; all-optional fields keeps parity with Sprint 1's `UpdateRoleSerializer` convention and avoids forcing clients to resend the full record. |
| Soft delete via `is_deleted`/`deleted_at`, not a status flag | `status` (ACTIVE/INACTIVE/BLOCKED) is a *business* lifecycle the customer can move in and out of; deletion is a separate, one-way, audit-relevant event. Conflating them would make "reactivate" and "undelete" ambiguous. |
| `customer_code`/`phone` uniqueness checked against `all_objects` | The DB columns are unique across the whole table regardless of `is_deleted` (not partial/scoped). Checking only the soft-delete-filtered `objects` manager would let a serializer accept a code that then fails at the DB layer with a raw `IntegrityError`. |
| `GenericAPIView` instead of plain `APIView` for Customer views | Sprint 1's views are plain `APIView` because they don't need pagination/search/filter. Customer list requires all three, and `REST_FRAMEWORK.DEFAULT_FILTER_BACKENDS` is already configured project-wide for exactly this — reimplementing that machinery by hand in a plain `APIView` would duplicate DRF internals for no benefit. |
| `permissions.py` per app holds only dict constants, not new permission classes | `HasPermission` (Sprint 1) is already generic over action/resource; every future resource module should follow this same reuse pattern instead of writing bespoke `IsXxxPermission` classes. |
| `Customer.Export` permission declared, no export endpoint yet | Requested by the RBAC spec for this sprint, but no export endpoint was in the API scope — declaring the permission now avoids a migration later without shipping unused surface area. |

## Files Changed

### New Files

- `apps/customers/__init__.py`, `apps.py`, `admin.py`
- `apps/customers/constants.py`, `validators.py`, `managers.py`, `models.py`
- `apps/customers/selectors.py`, `serializers.py`, `services.py`
- `apps/customers/permissions.py`, `exceptions.py`
- `apps/customers/views.py`, `urls.py`
- `apps/customers/migrations/0001_initial.py`
- `apps/customers/tests/__init__.py`, `test_customer.py`
- `conftest.py` (project root — fixture re-export fix)
- `docs/sprint_2.md`

### Modified Files

- `config/settings/base.py` — added `apps.customers` to `LOCAL_APPS`.
- `config/urls.py` — included `apps.customers.urls` under `api/v1/`.
- `shared/pagination.py` — added `paginated_success_response()` helper.
- `tests/conftest.py` — added customer fixtures (`customer_data`,
  `create_customer`, `*_customer_permission`, `customer_manager_role`,
  `user_with_customer_role`, `authenticated_customer_client`).
- `README.md` — added Customer Management API docs, updated project structure,
  added the "Coding Standards & Implementation Rules" section.

## Next Sprint

**Sprint 3 (proposed): Product & Inventory Management** — Category/Product
CRUD, stock tracking, `Product.*` RBAC — built on the same layered pattern and
`shared.pagination.paginated_success_response` established here.

## Addendum — Session-based Dashboard UI (2026-07-31)

`/` was originally a redirect to `/api/v1/health/` (Sprint 0), then briefly a
JSON module directory (`config.views.HomeView`). Following a request for an
actual browser-usable admin screen — login as a regular user, not
`is_staff`-gated Django Admin — a new `apps/dashboard` app was added:

- `/` — dashboard home (module directory, gated per-module by RBAC).
- `/login/`, `/logout/` — Django session auth (`authenticate()`/`login()`/
  `logout()`), independent of the JWT flow used by `/api/v1/auth/...`.
- `/customers/`, `/customers/create/`, `/customers/{id}/edit/`,
  `/customers/{id}/delete/` — full HTML CRUD for the Customer Management
  module built in this sprint, permission-gated the same way as the API
  (`view`/`create`/`update`/`delete:customer`).
- `config.views.HomeView` (the JSON directory) moved to `/api/v1/` — a
  cleaner location for an API-consumer-facing index, and it stopped
  colliding with the new browser-facing `/`.

New reusable primitives (documented in README § Coding Standards, mục 11):
`apps.dashboard.decorators.require_permission` (the session-view equivalent
of `HasPermission`, calling the same `PermissionSelector`) and
`CustomerSelector.search_customers()` (a plain-queryset search/filter method
for views without DRF filter backends). Both `apps/accounts` and
`apps/customers` were otherwise unmodified — the dashboard only *consumes*
their Service/Selector layers, never duplicates their logic.

21 new tests added (`apps/dashboard/tests/test_dashboard.py`), using Django's
`client` fixture with real `client.login()` sessions (not
`APIClient.force_authenticate`, which doesn't apply to plain Django views).
