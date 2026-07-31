# Sprint 1 — Authentication & RBAC

**Completed:** 2026-07-30

## Summary

Sprint 1 implements JWT Authentication and Role-Based Access Control (RBAC)
for the POS Management System.

## What Was Built

### Authentication (6 endpoints)
- **Login** (`POST /api/v1/auth/login/`) — Email + password, returns JWT pair + user data
- **Logout** (`POST /api/v1/auth/logout/`) — Blacklists refresh token
- **Refresh** (`POST /api/v1/auth/refresh/`) — Rotates access + refresh tokens
- **Current User** (`GET /api/v1/auth/me/`) — Returns authenticated user profile
- **Update Profile** (`PATCH /api/v1/auth/me/`) — Updates full_name, phone
- **Change Password** (`POST /api/v1/auth/change-password/`) — With old password validation

### RBAC (6 endpoints + 3 models)
- **Permission Model** — Action-resource pattern with TextChoices
  - Actions: create, read, update, delete, export, import, approve, view
  - Resources: user, role, customer, product, category, inventory, invoice, order, payment, dashboard, report
- **Role Model** — Named permission collections with active/inactive toggle
- **UserRole Model** — Through model with audit trail (assigned_by, assigned_at)
- **HasPermission** — Reusable DRF permission class (view-attribute + factory method patterns)
- **PermissionSelector** — Superuser bypass, role-based permission checking

### Services Layer
- **AuthService** — login, logout, refresh_token, change_password
- **UserService** — update_profile
- **RoleService** — create_role, update_role, delete_role, assign_role_to_user, remove_role_from_user

### Tests
- **test_auth.py** — 14 tests (login, logout, refresh, current user, change password)
- **test_rbac.py** — 19 tests (models, selectors, API endpoints)
- **test_user.py** — 7 tests (relationships, serialization)

## Design Decisions

| Decision | Rationale |
|---|---|
| Action-resource permissions (not Django Groups) | Supports Export/Import/Approve actions; more granular than built-in |
| TextChoices for actions/resources | Type safety, DB validation, IDE autocomplete |
| Superuser bypasses RBAC | Reduces friction for admin; consistent with Django convention |
| Token blacklisting on logout | Prevents reuse of refresh tokens after explicit logout |
| Through model for UserRole | Audit trail: who assigned the role and when |
| `HasPermission.with_permission()` factory | Cleaner DRF permission declaration without view attributes |

## Files Changed

### New Files
- `apps/accounts/tests/test_auth.py`
- `apps/accounts/tests/test_rbac.py`
- `apps/accounts/tests/test_user.py`

### Modified Files
- `apps/accounts/models.py` — Added Permission, Role, UserRole models + User.roles M2M
- `apps/accounts/constants.py` — Added PermissionAction, PermissionResource, auth messages
- `apps/accounts/exceptions.py` — Added auth-specific exceptions
- `apps/accounts/serializers.py` — Added 10 serializers (auth + RBAC)
- `apps/accounts/services.py` — Added AuthService, UserService, RoleService
- `apps/accounts/selectors.py` — Added UserSelector, PermissionSelector, RoleSelector
- `apps/accounts/permissions.py` — Added HasPermission, IsSuperAdmin
- `apps/accounts/views.py` — Added 8 views (auth + RBAC)
- `apps/accounts/urls.py` — Added 9 routes
- `apps/accounts/admin.py` — Registered RBAC models
- `config/settings/base.py` — Added token_blacklist to INSTALLED_APPS
- `shared/constants.py` — Added auth messages
- `tests/conftest.py` — Added RBAC fixtures
- `README.md` — Updated API documentation

## Next Sprint

**Sprint 2: Customer Management** — CRUD, Search, Pagination, Filtering, Permission-based access.
