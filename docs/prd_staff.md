# PRD: Staff Management (Nhân viên & Vai trò)

## 1. Thông tin chung
- Module: Staff Management (User + Role)
- Sprint dự kiến: 6 (sau Report Management — Sprint 5)
- Người viết PRD: _(retroactive — viết lại sau khi đã triển khai, đối chiếu
  từ `docs/sprint_6.md`)_
- Ngày: 2026-09-12
- Trạng thái: Approved (đã triển khai, đã merge vào `develop` qua PR #6)

## 2. Bối cảnh & Vấn đề (Problem Statement)

Hệ thống RBAC (`User`, `Role`, `Permission`, `UserRole`,
`HasPermission`/`PermissionSelector`) đã có đầy đủ từ Sprint 1, kể cả API
quản lý Role (`/api/v1/roles/`) và logic gán role cho user
(`RoleService.assign_role_to_user`/`remove_role_from_user`). Nhưng **không
có bất kỳ endpoint hay giao diện nào để tạo tài khoản nhân viên mới** —
cách duy nhất là chạy `python manage.py createsuperuser` qua CLI trong
container, không khả dụng cho người quản lý cửa hàng không có quyền truy
cập server.

Hệ quả trực tiếp: tài khoản dev mặc định `admin@pos.com` mà README hứa hẹn
"đăng nhập được ngay sau `docker compose up --build`" **không hề tồn tại**
cho tới khi ai đó chạy lệnh CLI thủ công — một lỗ hổng phát hiện được khi
kiểm thử thực tế. Cần giải quyết bây giờ vì đây là điều kiện tiên quyết để
onboard nhân viên thật và để kiểm thử RBAC end-to-end (tạo role → gán
permission → gán cho user → xác nhận user đó chỉ làm được đúng việc được
phép).

## 3. Mục tiêu (Goals)

- Mục tiêu 1: Người có quyền tạo được tài khoản nhân viên mới (email, họ
  tên, mật khẩu, SĐT tuỳ chọn) và gán ngay 0..n vai trò có sẵn, qua cả REST
  API lẫn giao diện Dashboard.
- Mục tiêu 2: Người có quyền tạo được **vai trò (Role) mới** ngay trong
  luồng quản lý nhân viên — đặt tên, mô tả, và chọn permission theo từng
  module nghiệp vụ — để không bị chặn bởi việc "chưa có role phù hợp" khi
  tạo nhân viên.
- Mục tiêu 3: Vô hiệu hoá được một nhân viên nghỉ việc mà **không xoá cứng**
  tài khoản (bảo toàn lịch sử `created_by`/`updated_by` trên Customer,
  Order, Invoice... mà nhân viên đó từng thao tác).
- Mục tiêu 4: Kích hoạt lại được một nhân viên đã vô hiệu hoá (ví dụ quay
  lại làm việc) mà không cần tạo tài khoản mới hay đặt lại mật khẩu.
- Mục tiêu 5 (đo lường được): từ lúc admin đăng nhập đến lúc tạo xong 1
  nhân viên mới có thể đăng nhập ngay — dưới 2 phút thao tác trên UI, không
  cần chạm tới CLI/server.

## 4. Ngoài phạm vi (Non-goals / Out of Scope)

- **Đổi email nhân viên sau khi tạo** — email là định danh đăng nhập cố
  định trong phạm vi sprint này.
- **Xoá cứng (hard delete) tài khoản nhân viên** — "Delete" trong toàn bộ
  PRD này luôn là vô hiệu hoá (`is_active=False`), không phải xoá bản ghi.
- **UI xoá Role** — `RoleService.delete_role` (kèm guard "role đang có
  người dùng") đã có từ Sprint 1 nhưng chỉ dùng qua API/Admin; không thêm
  nút xoá role trên Dashboard ở sprint này.
- **Seed permission catalog tự động cho môi trường production** — việc
  seed đầy đủ action×resource permission chỉ có trong lệnh
  `seed_demo_data` (dev-only, tách biệt khỏi PRD này); production cần seed
  permission thủ công qua Django Admin.
- **Quy trình duyệt (approval workflow)** khi tạo nhân viên mới hoặc đổi
  vai trò — tạo/sửa có hiệu lực ngay lập tức.
- **Đặt lại mật khẩu qua email** (quên mật khẩu) — chỉ admin đổi trực tiếp
  qua form sửa nhân viên.
- **Giới hạn số vai trò tối đa trên một nhân viên** — không giới hạn.

## 5. Đối tượng sử dụng (Actors / User Roles)

| Actor | Vai trò trong module này |
|---|---|
| Quản lý / Admin (có `create/update/delete:user`, `create/update:role`) | Tạo, sửa, vô hiệu hoá, kích hoạt lại nhân viên; tạo và sửa vai trò kèm permission. |
| Nhân viên chỉ có `view:user`/`view:role` | Chỉ xem danh sách nhân viên/vai trò, không sửa được gì. |
| Superuser | Toàn quyền, bypass RBAC như mọi module khác. |

## 6. Entity nghiệp vụ

Module này **không tạo entity mới** — `User`, `Role`, `Permission`,
`UserRole` đã tồn tại từ Sprint 1. PRD này bổ sung *chức năng* (tạo, sửa,
vô hiệu hoá/kích hoạt User; tạo, sửa Role) trên các entity đó.

### User (đã có, liệt kê lại để tham chiếu)

| Field | Bắt buộc? | Unique? | Ghi chú |
|---|---|---|---|
| email | Có | Có | Định danh đăng nhập, không phân biệt hoa/thường khi kiểm tra trùng |
| full_name | Có | Không | |
| phone | Không | Không | Không có validate định dạng bắt buộc (khác `Customer.phone`) |
| password | Có lúc tạo, không bắt buộc lúc sửa | — | Luôn được hash, không bao giờ trả plaintext qua API |
| is_active | Không (mặc định `true`) | Không | Đóng vai trò "trạng thái" của module này — xem mục Trạng thái |
| roles | Không | — | M2M tới Role qua `UserRole`, giữ `assigned_by`/`assigned_at` |

### Trạng thái (Status) — `User.is_active`

| Giá trị | Ý nghĩa | Chuyển từ trạng thái nào |
|---|---|---|
| `true` (Đang hoạt động) | Đăng nhập được, thao tác bình thường | (trạng thái khởi tạo khi tạo mới) |
| `false` (Đã vô hiệu hoá) | Không đăng nhập được, dữ liệu cũ vẫn giữ nguyên | `true` (qua hành động Vô hiệu hoá) |

Đi ngược lại (`false` → `true`) qua hành động Kích hoạt lại — đây là vòng
trạng thái hai chiều duy nhất trong dự án (khác `Customer`/`Product` chỉ
xoá mềm một chiều).

### Role (đã có, liệt kê lại để tham chiếu)

| Field | Bắt buộc? | Unique? | Ghi chú |
|---|---|---|---|
| name | Có | Có | |
| description | Không | Không | |
| is_active | Không (mặc định `true`) | Không | |
| permissions | Không | — | M2M tới `Permission`, chọn qua ma trận Module × Action ở FR-6 |

## 7. Quan hệ với module khác (Dependencies)

- Mọi module nghiệp vụ khác (Customer, Product, Order, Invoice, Payment,
  Inventory) tham chiếu `User` qua `created_by`/`updated_by`
  (`on_delete=SET_NULL`) — đây chính là lý do PRD này chọn **vô hiệu hoá
  thay vì xoá cứng**: xoá cứng sẽ không phá vỡ dữ liệu (đã là `SET_NULL`)
  nhưng sẽ xoá mất thông tin "ai đã tạo/sửa" trên toàn bộ lịch sử nghiệp vụ.
- Role tham chiếu Permission (không đổi từ Sprint 1).
- Không cần Soft Delete kiểu `is_deleted`/`deleted_at` cho `User` — trạng
  thái nhị phân `is_active` đã đủ diễn đạt nghiệp vụ "còn làm việc hay
  không", khác với `Customer.status` (một trạng thái nghiệp vụ nhiều giá
  trị) cộng thêm cờ xoá mềm riêng.

## 8. Chức năng (Functional Requirements)

### FR-1: Tạo nhân viên (Create Staff)
- Mô tả: Actor có quyền `create:user` nhập email, họ tên, mật khẩu, SĐT
  (tuỳ chọn), chọn 0..n vai trò có sẵn, tạo tài khoản mới.
- Acceptance Criteria:
  - [x] Email trùng (không phân biệt hoa/thường) bị từ chối kèm thông báo
        rõ ràng.
  - [x] Mật khẩu bắt buộc khi tạo, được kiểm tra qua bộ validator mật khẩu
        chuẩn của Django.
  - [x] Chỉ chọn được vai trò đang tồn tại; role_id không hợp lệ bị từ
        chối.
  - [x] Tạo thành công trả về thông tin nhân viên (không kèm mật khẩu) và
        danh sách vai trò đã gán.
  - [x] Trường hợp lỗi: thiếu quyền `create:user` → 403.

### FR-2: Danh sách & tìm kiếm nhân viên
- Mô tả: Actor có quyền `view:user` xem danh sách nhân viên, tìm theo
  email/họ tên/SĐT, lọc theo trạng thái hoạt động, có phân trang.
- Acceptance Criteria:
  - [x] Tìm kiếm khớp một trong ba field: email, full_name, phone.
  - [x] Lọc được theo `is_active=true|false`.
  - [x] Phân trang theo chuẩn chung của dự án (`page`, `page_size`).
  - [x] Trường hợp lỗi: thiếu quyền `view:user` → 403.

### FR-3: Sửa thông tin & vai trò nhân viên
- Mô tả: Actor có quyền `update:user` sửa họ tên/SĐT/trạng thái hoạt
  động/mật khẩu (tuỳ chọn)/tập vai trò đang gán.
- Acceptance Criteria:
  - [x] Đổi tập vai trò = gán vai trò mới được chọn + gỡ vai trò không còn
        được chọn (diff hai chiều), không ghi đè toàn bộ M2M.
  - [x] `assigned_by`/`assigned_at` của các vai trò không đổi được giữ
        nguyên (không tạo lại record gán).
  - [x] Để trống ô mật khẩu khi sửa nghĩa là không đổi mật khẩu.
  - [x] Email không sửa được qua chức năng này.
  - [x] Trường hợp lỗi: thiếu quyền `update:user` → 403; user không tồn
        tại → 404.

### FR-4: Vô hiệu hoá nhân viên (Deactivate)
- Mô tả: Actor có quyền `delete:user` vô hiệu hoá một tài khoản
  (`is_active=false`); tài khoản không đăng nhập được nữa nhưng vẫn còn
  nguyên trong hệ thống.
- Acceptance Criteria:
  - [x] Sau khi vô hiệu hoá, đăng nhập bằng tài khoản đó bị từ chối.
  - [x] Dữ liệu nghiệp vụ do nhân viên đó tạo trước đây không bị ảnh
        hưởng hay ẩn đi.
  - [x] Không có endpoint/hành động nào xoá cứng bản ghi `User`.
  - [x] Trường hợp lỗi: thiếu quyền `delete:user` → 403.

### FR-5: Kích hoạt lại nhân viên (Reactivate)
- Mô tả: Actor có quyền `update:user` kích hoạt lại một tài khoản đã bị vô
  hiệu hoá, cho phép đăng nhập trở lại ngay.
- Acceptance Criteria:
  - [x] Chỉ hiển thị hành động này cho tài khoản đang ở trạng thái
        `is_active=false`.
  - [x] Sau khi kích hoạt, đăng nhập lại thành công ngay với **mật khẩu
        cũ** (không yêu cầu đặt lại mật khẩu).
  - [x] Trường hợp lỗi: thiếu quyền `update:user` → 403.

### FR-6: Tạo vai trò (Create Role)
- Mô tả: Actor có quyền `create:role` đặt tên + mô tả cho vai trò mới, chọn
  permission theo **ma trận Module × Xem/Tạo/Sửa/Xoá** (các action khác
  ngoài 4 loại chính, như Export/Approve, hiển thị ở cột "Khác" để không
  bỏ sót).
- Acceptance Criteria:
  - [x] Tên vai trò không được trùng với vai trò đã có.
  - [x] Vai trò tạo xong xuất hiện ngay trong danh sách có thể gán khi
        tạo/sửa nhân viên (không cần tải lại trang/khởi động lại hệ
        thống).
  - [x] Cho phép tạo vai trò không kèm permission nào (vai trò rỗng, gán
        sau).
  - [x] Mỗi ô trong ma trận chỉ hiển thị checkbox nếu module đó thực sự có
        permission tương ứng đã tồn tại trong hệ thống; nếu không, ô hiển
        thị "—".
  - [x] Trường hợp lỗi: thiếu quyền `create:role` → 403 (Dashboard) / 403
        (API); tên trùng → lỗi validation, không tạo trùng.

### FR-7: Sửa vai trò (Update Role)
- Mô tả: Actor có quyền `update:role` đổi tên/mô tả/tập permission của một
  vai trò đã có.
- Acceptance Criteria:
  - [x] Đổi permission có hiệu lực ngay cho **mọi** nhân viên đang giữ vai
        trò đó (kiểm tra quyền là real-time theo vai trò hiện tại, không
        cần đăng nhập lại).
  - [x] Đổi tên phải không trùng vai trò khác (trừ chính nó).
  - [x] Trường hợp lỗi: thiếu quyền `update:role` → 403; role không tồn
        tại → 404/thông báo lỗi.

### FR-8: Danh sách vai trò
- Mô tả: Actor có quyền `view:role` xem danh sách vai trò kèm số permission
  và số nhân viên đang giữ mỗi vai trò.
- Acceptance Criteria:
  - [x] Hiển thị đúng số đếm permission/nhân viên tại thời điểm xem (không
        cache sai lệch).
  - [x] Trường hợp lỗi: thiếu quyền `view:role` → 403.

## 9. Quy tắc nghiệp vụ & Validation

- Email là định danh đăng nhập duy nhất trong toàn hệ thống, so khớp trùng
  không phân biệt hoa/thường.
- Mật khẩu khi tạo mới bắt buộc và phải vượt qua bộ validator mật khẩu mặc
  định của Django (độ dài tối thiểu, không phải mật khẩu phổ biến, không
  toàn số...).
- Tên vai trò (`Role.name`) phải duy nhất trong toàn hệ thống.
- Gán/gỡ vai trò cho nhân viên phải đi qua service gán vai trò sẵn có (giữ
  `assigned_by`/`assigned_at`) — không được thao tác trực tiếp trên bảng
  trung gian.
- "Xoá" nhân viên trong toàn bộ PRD này luôn được hiểu là vô hiệu hoá
  (`is_active=false`); không có khái niệm xoá cứng.
- SĐT nhân viên không bắt buộc và không có ràng buộc unique (khác `Customer.phone`).

## 10. Phân quyền (RBAC — theo nghiệp vụ, không phải tên class)

| Action | Actor được phép |
|---|---|
| Xem nhân viên (View) | Actor có `view:user`; Superuser luôn được phép |
| Tạo nhân viên (Create) | Actor có `create:user`; Superuser |
| Sửa nhân viên / Kích hoạt lại (Update) | Actor có `update:user`; Superuser |
| Vô hiệu hoá nhân viên (Delete) | Actor có `delete:user`; Superuser |
| Xem vai trò (View) | Actor có `view:role`; Superuser |
| Tạo vai trò (Create) | Actor có `create:role`; Superuser |
| Sửa vai trò (Update) | Actor có `update:role`; Superuser |

Không có hành động "Xoá vai trò" trong phạm vi PRD này (xem mục 4 — Ngoài
phạm vi).

## 11. Yêu cầu phi chức năng (Non-functional, nếu có)

- **Bảo mật**: mật khẩu luôn được hash trước khi lưu; không endpoint nào
  trả về mật khẩu (kể cả đã hash) trong response.
- **Nhất quán RBAC**: cùng một logic kiểm tra quyền dùng chung cho cả REST
  API và Dashboard (không viết hai lần hai nơi khác nhau) — đảm bảo một
  nhân viên bị chặn giống nhau dù dùng API hay giao diện web.
- **Hiệu lực tức thời**: thay đổi vai trò/permission có hiệu lực ngay ở
  lần request tiếp theo, không cần nhân viên đăng xuất/đăng nhập lại.
- **Khả năng phục hồi**: vô hiệu hoá nhân viên phải là hành động đảo ngược
  được hoàn toàn (không mất dữ liệu, không cần tạo lại tài khoản).

## 12. Câu hỏi mở / Rủi ro (Open Questions / Risks)

- Có cần giới hạn số lượng vai trò tối đa gán cho một nhân viên không?
  Hiện tại không giới hạn — cần xác nhận đây có phải rủi ro vận hành
  (nhân viên có quá nhiều quyền chồng chéo) hay không.
- Nhu cầu đổi email nhân viên sau khi tạo có thực sự phát sinh trong vận
  hành thực tế không, hay giữ nguyên out-of-scope?
- Catalog permission (action × resource) hiện chỉ được seed đầy đủ qua
  script dev-only (`seed_demo_data`) — cần chốt quy trình seed cho môi
  trường production trước khi go-live thật (qua Django Admin thủ công hay
  một management command riêng cho production?).
- Có cần cảnh báo trên UI khi tạo một vai trò rỗng (0 permission) để tránh
  nhầm lẫn "tạo xong mà không có tác dụng gì" không?

## 13. Bước tiếp theo

- [x] PRD được review & approve bởi: _(retroactive — đã triển khai và
      merge vào `develop`)_
- [x] Convert sang prompt kỹ thuật theo [`docs/prompt-features.md`](prompt-features.md)
- [x] Triển khai theo [README.md § Quy tắc Coding & Triển khai](../README.md#quy-tắc-coding--triển-khai)
- [x] Ghi lại kết quả tại [`docs/sprint_6.md`](sprint_6.md)
