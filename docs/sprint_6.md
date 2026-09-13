# Sprint 6 — Staff Management (Add User + phân quyền)

**Trạng thái:** Hoàn thành
**Ngày hoàn thành:** 2026-09-12

## Mục tiêu

Cho phép người có quyền tạo tài khoản nhân viên (staff) mới và gán vai trò
(role) có sẵn cho họ — cả qua REST API lẫn qua trang Dashboard UI. Trước
sprint này, hệ thống RBAC (User/Role/Permission/UserRole,
`RoleService.assign_role_to_user`) đã tồn tại đầy đủ nhưng không có bất kỳ
endpoint hay UI nào để tạo nhân viên, khiến tài khoản dev `admin@pos.com`
trong README phải được tạo thủ công bằng `createsuperuser` qua CLI.

## Công việc đã hoàn thành

- Bổ sung `UserService.create_user` / `update_user` / `deactivate_user` — tái
  sử dụng `RoleService.assign_role_to_user`/`remove_role_from_user` có sẵn
  cho việc gán/gỡ role thay vì thao tác trực tiếp trên M2M, để giữ được
  `assigned_by` trên `UserRole`.
- Bổ sung `UserSelector.search_users` (tìm theo email/tên/SĐT, lọc
  `is_active`) và `UserSelector.email_exists` (kiểm tra trùng email).
- Bổ sung API `GET/POST /api/v1/users/` và `GET/PATCH/DELETE
  /api/v1/users/{id}/`, dùng `HasPermission` + `PermissionResource.USER` có
  sẵn (`view:user`, `create:user`, `update:user`, `delete:user`).
- Bổ sung serializers (`CreateUserSerializer`, `UpdateUserSerializer`,
  `UserListSerializer`, `UserDetailSerializer`) và exceptions
  (`UserNotFoundError`, `UserAlreadyExistsError`).
- Bổ sung trang Dashboard "Nhân viên" (`/staff/`, `/staff/create/`,
  `/staff/{id}/edit/`, `/staff/{id}/deactivate/`) theo đúng pattern
  Customer (`StaffForm`, `staff_list/create/edit/deactivate` view,
  templates `dashboard/staff/{list,form}.html`), gán role qua checkbox list.
- Bổ sung trang Dashboard "Vai trò" (`/staff/roles/`, `/staff/roles/create/`,
  `/staff/roles/{id}/edit/`) — list role kèm số quyền/số nhân viên, form
  tạo/sửa role với chọn permission chi tiết (`RoleForm`,
  `role_list/create/edit` view, templates `dashboard/roles/{list,form}.html`).
  Tái sử dụng nguyên vẹn `RoleService.create_role`/`update_role` và
  `RoleSelector` đã có từ Sprint 1 — không viết lại logic RBAC, chỉ bọc UI.
  Trang Nhân viên có link "Quản lý vai trò" trỏ sang, và form tạo nhân viên
  có link "+ Tạo vai trò mới" trỏ ngược lại, để role vừa tạo dùng được ngay
  khi gán cho nhân viên.
- Form tạo/sửa Role hiển thị permission dưới dạng **ma trận Module ×
  Xem/Tạo/Sửa/Xoá** (`_build_permission_matrix` trong `apps/dashboard/views.py`)
  thay vì checkbox phẳng — mỗi hàng là một resource (Customer, Product,
  User...), 4 cột cố định theo action chính; action ngoài 4 cột này
  (Export, Approve...) vẫn hiển thị ở cột "Khác" để không mất dữ liệu khi
  lưu lại một role đã có sẵn permission loại đó.
- Cập nhật `config/views.py` (`FEATURE_MODULES["users"]`) và README (bảng API
  JSON + bảng session UI, gồm cả 3 route Role UI mới).

## Quyết định thiết kế

- **Delete = deactivate**: `DELETE /api/v1/users/{id}/` set `is_active=False`
  thay vì xoá cứng. `User` không tham gia pattern soft-delete
  (`is_deleted`/`deleted_at`) của các entity nghiệp vụ khác — tài khoản đăng
  nhập chỉ cần vô hiệu hoá (đảo ngược được), không cần lịch sử "đã xoá lúc
  nào" như Customer/Product.
- **`role_ids` qua `RoleService` thay vì `M2M.set()` trực tiếp**: through
  model `UserRole` có field `assigned_by`/`assigned_at` cần giữ nguyên khi
  gán mới; `update_user` diff role hiện tại vs role mới bằng `set()` rồi gọi
  `assign_role_to_user`/`remove_role_from_user` cho phần chênh lệch, thay vì
  ghi đè toàn bộ M2M (sẽ mất `assigned_by` của các role không đổi).
- **Không xây thêm UI Role/Permission**: phạm vi đã chốt là gán role *có
  sẵn* cho user; tạo Role mới / gán Permission cho Role đã có API
  `/api/v1/roles/` từ Sprint 1 và nằm ngoài phạm vi sprint này.
- **Không tạo app `apps/staff` riêng**: tính năng này thuộc về chính module
  User/RBAC, nên mở rộng `apps/accounts` trực tiếp (đúng ngoại lệ nêu ở
  `docs/prompt-features.md` mục 9), không tạo app mới hay đụng vào các app
  khác.
- **Route Role UI nằm dưới `/staff/roles/...`** (không phải module riêng ở
  trang chủ dashboard): theo yêu cầu, đây là công cụ phụ trợ cho việc tạo
  nhân viên (chọn/khởi tạo role để gán), không phải một module nghiệp vụ
  độc lập — nên gắn vào trang Nhân viên thay vì thêm thẻ module mới ở `/`.
- **Không có UI xoá Role**: `RoleService.delete_role` đã có guard
  `RoleHasUsersError`, nhưng xoá Role là hành động hiếm và rủi ro cao hơn
  deactivate User; giữ nguyên như cũ (chỉ xoá được qua API/Admin) để không
  mở rộng phạm vi ngoài yêu cầu.
- **Catalog Permission (action × resource) không được seed sẵn** ở bất kỳ
  đâu trong dự án (không có data migration/management command) — đây là gap
  có từ trước, không phải lỗi của sprint này. Trên môi trường dev mới, danh
  sách checkbox permission ở form tạo Role sẽ trống cho đến khi
  superuser tạo Permission thủ công qua Django Admin (`/admin/`, model đã
  đăng ký sẵn). Nên cân nhắc thêm seed command ở sprint sau.

## Bổ sung sau review: kích hoạt lại nhân viên

Trang Nhân viên chỉ có nút "Vô hiệu hoá" ban đầu, không có cách nào đảo
ngược ngoài việc mở form sửa và tick lại "Đang hoạt động". Bổ sung:

- `UserService.activate_user` (đối xứng với `deactivate_user` đã có).
- `POST /staff/{id}/activate/` (`staff_activate` view, quyền `update:user` —
  khác với `delete:user` của deactivate, vì đây là phục hồi trạng thái chứ
  không phải một hành động phá huỷ).
- Nút "Kích hoạt lại" trong `dashboard/staff/list.html`, chỉ hiện khi nhân
  viên đang ở trạng thái vô hiệu hoá.
- Test `TestActivateUser` (service-level + qua `PATCH is_active=true` của
  API đã có sẵn).

## Demo data seeding

Bổ sung `python manage.py seed_demo_data`
(`apps/accounts/management/commands/seed_demo_data.py`), tự động chạy trong
`scripts/entrypoint.sh` mỗi lần container `backend` khởi động (chỉ khi
`DJANGO_SETTINGS_MODULE=config.settings.development`; command tự từ chối
chạy nếu `DEBUG=False` — không bao giờ đụng production dù bị gọi nhầm).
Idempotent hoàn toàn (get_or_create/existence check theo key duy nhất —
email, customer_code, action+resource) nên chạy lại (mỗi lần restart
container) không tạo trùng dữ liệu. Seed:

- Superuser dev `admin@pos.com` / `PosDev@2026!` (README đã tài liệu hoá tài
  khoản này từ trước nhưng chưa từng có gì tự tạo nó — sprint này khép lại
  luôn lỗ hổng đó, không cần chạy `createsuperuser` thủ công nữa).
- Catalog permission đầy đủ (33 permission — action × resource cho mọi
  action/resource thực sự được `require_permission`/`required_permission`
  dùng ở đâu đó trong code).
- 4 Role theo vị trí thực tế: *Quản lý cửa hàng* (toàn quyền nghiệp vụ),
  *Thu ngân*, *Nhân viên kho*, *Nhân viên bán hàng* — mỗi role chỉ có đúng
  permission cần cho công việc của vị trí đó.
- 15 tài khoản nhân viên (`nhanvien01@pos.com`…`nhanvien15@pos.com`, mật
  khẩu mặc định `12345678@`), phân bổ 2/4/4/5 theo 4 vị trí trên.
- 100 khách hàng (`CUS0001`…`CUS0100`) với tên/địa chỉ tiếng Việt qua
  `Faker("vi_VN")`, seed cố định (`Faker.seed(20260912)`) để dữ liệu sinh ra
  giống nhau giữa các lần chạy.
- 10 danh mục (`CategoryService.create_category`) × 10 sản phẩm/danh mục
  (`ProductService.create_product`, `SKU0001`…`SKU0100`) — tên sản phẩm thật
  theo từng ngành hàng (đồ uống, bánh kẹo, gia vị, mỹ phẩm...), mỗi danh mục
  gán 1 đơn vị tính (`ProductUnit`) đại diện. Mỗi sản phẩm được nhập kho ban
  đầu qua `InventoryService.record_movement` (INBOUND) với số lượng lấy từ
  10 mức cố định (`STOCK_LEVELS = (3, 8, 15, 25, 40, 60, 90, 120, 200, 350)`)
  lặp vòng qua từng sản phẩm — tồn kho rải đều từ sắp hết đến dư dả, đủ để
  test filter theo `stock_status` (`out_of_stock`/`low_stock`/`in_stock`)
  và sắp xếp theo số lượng.

## Sự cố môi trường phát hiện (ngoài phạm vi sprint, đã xử lý tối thiểu)

- `apps/orders/migrations/`, `apps/invoices/migrations/`,
  `apps/payments/migrations/` thiếu file `__init__.py`, khiến Django coi 3
  app này là "unmigrated" và toàn bộ test suite không chạy được (kể cả test
  đã có từ trước, không liên quan Staff). Đã bổ sung 3 file `__init__.py`
  rỗng để khôi phục khả năng chạy test — không đổi logic nghiệp vụ nào.
- Sau khi migrations của `orders` được nhận diện đúng,
  `apps/orders/tests/test_order_flow.py::test_existing_product_flows_to_order_invoice_and_payment`
  lộ ra một lỗi có sẵn (vi phạm constraint `order_total_positive` khi tạo
  Order với `total_amount=0` trước khi tính lại) — **không sửa trong sprint
  này** vì ngoài phạm vi Staff Management; cần một task riêng cho module
  Order.

## Kiểm thử

- Bổ sung 11 test cho Staff (`apps/accounts/tests/test_staff.py`): tạo user
  (thành công/email trùng/thiếu quyền/superuser bypass), list/search/filter,
  cập nhật role (gán + gỡ), deactivate (thành công/thiếu quyền).
- Toàn bộ `apps/accounts/`: **64 test passed**, coverage **85.30%**, đạt yêu
  cầu tối thiểu 80%.
- Xác minh thủ công qua trình duyệt: tạo nhân viên mới tại `/staff/create/`
  với role "Staff", đăng nhập lại bằng tài khoản vừa tạo — hoạt động đúng.

## Hướng tích hợp sprint sau

- Trang UI quản lý Role/Permission (tạo role mới, chọn permission cho role)
  nếu nghiệp vụ cần thao tác này ngoài Django Admin.
- Sửa lỗi `order_total_positive` phát hiện ở `apps/orders` (không liên quan
  Staff, cần PRD/task riêng).
