# PRD: Customer Management (Khách hàng)

## 1. Thông tin chung
- Module: Customer (Khách hàng)
- Sprint dự kiến: 2 (sau Authentication & RBAC — Sprint 1)
- Người viết PRD: _(retroactive — viết lại sau khi đã triển khai, đối
  chiếu từ `docs/sprint_2.md`)_
- Ngày: 2026-09-12
- Trạng thái: Approved (đã triển khai từ 2026-07-31, đang hoạt động trên
  `develop`)

## 2. Bối cảnh & Vấn đề (Problem Statement)

Sau Sprint 1, hệ thống mới có Authentication và RBAC (User/Role/Permission)
nhưng **chưa có bất kỳ dữ liệu nghiệp vụ nào** để bán hàng. Một hệ thống
POS không thể vận hành nếu không quản lý được ai là khách mua hàng — không
lưu được thông tin liên hệ, không tra cứu được lịch sử, không phân biệt
được khách đang hoạt động/ngừng giao dịch/bị chặn.

Đây là module nghiệp vụ đầu tiên của hệ thống nên cần giải quyết ngay sau
RBAC: Customer là nền tảng bắt buộc để các module Order/Invoice/Payment ở
các sprint sau có đối tượng để gắn giao dịch vào — không có Customer,
không có gì để bán "cho ai".

## 3. Mục tiêu (Goals)

- Mục tiêu 1: Lưu trữ được thông tin khách hàng đầy đủ (mã khách hàng, họ
  tên, số điện thoại, email, giới tính, ngày sinh, địa chỉ, ghi chú) với mã
  khách hàng và số điện thoại là định danh duy nhất.
- Mục tiêu 2: Tìm kiếm, lọc theo trạng thái, sắp xếp và phân trang được
  danh sách khách hàng ở quy mô hàng nghìn bản ghi trở lên.
- Mục tiêu 3: Xoá một khách hàng khỏi danh sách hoạt động mà **không mất
  dữ liệu lịch sử** — vì các module Order/Invoice ra đời sau này sẽ tham
  chiếu đến khách hàng đã từng giao dịch.
- Mục tiêu 4: Toàn bộ thao tác tuân thủ đúng RBAC đã có từ Sprint 1, không
  tạo cơ chế phân quyền riêng cho module này.

## 4. Ngoài phạm vi (Non-goals / Out of Scope)

- **Xuất dữ liệu (Export) ra CSV/Excel** — quyền `export:customer` được
  khai báo sẵn trong RBAC để không cần migration sau này, nhưng **không có
  endpoint export nào** ship trong phạm vi PRD này.
- **Nhóm khách hàng (Customer Group/Tier)**, chương trình khách hàng thân
  thiết, tích điểm — để dành cho sprint sau nếu có nhu cầu.
- **Xoá cứng (hard delete)** khách hàng — chỉ có xoá mềm.
- **Khôi phục khách hàng đã xoá mềm qua UI** (không có "thùng rác" cho
  Customer như Product/Category) — khác với Product Management ở sprint
  sau.
- **Nhập liệu hàng loạt (bulk import)** khách hàng từ file.
- **Xác thực số điện thoại/email** (OTP, gửi email xác nhận) — chỉ validate
  định dạng, không xác minh khách hàng thực sự sở hữu số/email đó.

## 5. Đối tượng sử dụng (Actors / User Roles)

| Actor | Vai trò trong module này |
|---|---|
| Nhân viên có `create:customer`/`update:customer` | Tạo mới và cập nhật thông tin khách hàng khi phục vụ. |
| Nhân viên chỉ có `view:customer` | Tìm kiếm, tra cứu thông tin khách hàng, không sửa được. |
| Quản lý có `delete:customer` | Xoá mềm khách hàng không còn giao dịch. |
| Superuser | Toàn quyền, bypass RBAC như mọi module khác. |

## 6. Entity nghiệp vụ

### Customer

| Field | Bắt buộc? | Unique? | Ghi chú |
|---|---|---|---|
| customer_code | Có | Có | Mã nghiệp vụ, tối đa 20 ký tự (vd. `CUS000123`) |
| full_name | Có | Không | Tối đa 150 ký tự |
| phone | Có | Có | 9–15 chữ số, có thể có dấu `+` ở đầu |
| email | Không | Không | Định dạng email hợp lệ nếu có nhập |
| gender | Không | Không | `male` / `female` / `other` |
| birthday | Không | Không | Ngày sinh |
| address | Không | Không | Địa chỉ tự do (nhiều dòng) |
| note | Không | Không | Ghi chú tự do |
| status | Có | Không | Xem mục Trạng thái bên dưới |

### Trạng thái (Status)

| Giá trị | Ý nghĩa | Chuyển từ trạng thái nào |
|---|---|---|
| `active` | Đang giao dịch bình thường | (trạng thái khởi tạo khi tạo mới) |
| `inactive` | Tạm ngừng giao dịch (khách lâu không quay lại...) | `active`, `blocked` |
| `blocked` | Bị chặn giao dịch (vi phạm chính sách cửa hàng...) | `active`, `inactive` |

`status` là trạng thái **nghiệp vụ**, tách biệt hoàn toàn với cờ xoá mềm
(`is_deleted`) — một khách hàng có thể "bị chặn" (`blocked`) nhưng vẫn còn
hiển thị trong danh sách chính thức; chỉ khi bị xoá mềm mới biến mất khỏi
danh sách mặc định.

## 7. Quan hệ với module khác (Dependencies)

- Order, Invoice, Payment (xây dựng ở các sprint sau) tham chiếu tới
  `Customer.id` — khách hàng đã có giao dịch **không được xoá cứng** vì sẽ
  làm gãy lịch sử đơn hàng/hoá đơn.
- **Cần Soft Delete**: Có — `is_deleted`/`deleted_at`, đúng theo mặc định
  của dự án cho entity bị module khác tham chiếu. Danh sách mặc định
  (`Customer.objects`) tự động loại bản ghi đã xoá mềm; kiểm tra trùng
  `customer_code`/`phone` vẫn phải quét cả bản ghi đã xoá (`all_objects`)
  vì ràng buộc unique ở tầng database áp dụng cho toàn bảng, không loại
  trừ bản ghi đã xoá mềm.

## 8. Chức năng (Functional Requirements)

### FR-1: Tạo khách hàng (Create Customer)
- Mô tả: Actor có quyền `create:customer` nhập thông tin khách hàng mới.
- Acceptance Criteria:
  - [x] `customer_code` và `phone` không được trùng với khách hàng đang
        hoạt động lẫn đã xoá mềm.
  - [x] `phone` phải đúng định dạng 9–15 chữ số, có thể có `+` ở đầu.
  - [x] `status` mặc định `active` nếu không truyền.
  - [x] Trường hợp lỗi: thiếu quyền `create:customer` → 403; trùng mã/SĐT
        hoặc sai định dạng SĐT → lỗi validation rõ ràng, không tạo bản ghi.

### FR-2: Danh sách / Tìm kiếm / Lọc / Sắp xếp / Phân trang
- Mô tả: Actor có quyền `view:customer` xem danh sách khách hàng, tìm theo
  mã/họ tên/SĐT/email, lọc theo trạng thái, sắp xếp theo nhiều tiêu chí,
  phân trang.
- Acceptance Criteria:
  - [x] Tìm kiếm khớp một trong các field: `customer_code`, `full_name`,
        `phone`, `email`.
  - [x] Lọc được theo `status` (`active`/`inactive`/`blocked`).
  - [x] Sắp xếp được theo nhiều field, hỗ trợ chiều tăng/giảm.
  - [x] Phân trang theo chuẩn chung của dự án.
  - [x] Trường hợp lỗi: thiếu quyền `view:customer` → 403.

### FR-3: Xem chi tiết khách hàng
- Mô tả: Actor có quyền `view:customer` xem đầy đủ thông tin một khách
  hàng, kèm người tạo/người cập nhật gần nhất.
- Acceptance Criteria:
  - [x] Trả 404/thông báo rõ ràng nếu khách hàng không tồn tại hoặc đã bị
        xoá mềm.
  - [x] Trường hợp lỗi: thiếu quyền `view:customer` → 403.

### FR-4: Cập nhật khách hàng (Update Customer)
- Mô tả: Actor có quyền `update:customer` sửa thông tin khách hàng đã có,
  bao gồm cả đổi trạng thái nghiệp vụ (`active`/`inactive`/`blocked`).
- Acceptance Criteria:
  - [x] Tất cả field cho phép cập nhật từng phần (không bắt buộc gửi lại
        toàn bộ bản ghi).
  - [x] Đổi `customer_code`/`phone` vẫn phải qua kiểm tra trùng (loại trừ
        chính bản ghi đang sửa).
  - [x] Trường hợp lỗi: thiếu quyền `update:customer` → 403; khách hàng
        không tồn tại → 404.

### FR-5: Xoá khách hàng (Soft Delete)
- Mô tả: Actor có quyền `delete:customer` xoá mềm một khách hàng — biến
  mất khỏi danh sách mặc định nhưng dữ liệu và lịch sử tham chiếu vẫn còn
  nguyên trong hệ thống.
- Acceptance Criteria:
  - [x] Sau khi xoá mềm, khách hàng không còn xuất hiện trong danh sách
        mặc định (GET list) hay tìm kiếm.
  - [x] Bản ghi vẫn tồn tại trong database (`deleted_at` được ghi nhận),
        không bị xoá cứng.
  - [x] Trường hợp lỗi: thiếu quyền `delete:customer` → 403; khách hàng
        không tồn tại/đã xoá → 404.

## 9. Quy tắc nghiệp vụ & Validation

- `customer_code` bắt buộc, duy nhất, tối đa 20 ký tự.
- `phone` bắt buộc, duy nhất, đúng định dạng 9–15 chữ số (có thể có `+` ở
  đầu).
- `email` không bắt buộc, nhưng nếu nhập phải đúng định dạng email.
- Kiểm tra trùng `customer_code`/`phone` phải tính cả bản ghi đã xoá mềm
  (ràng buộc unique ở database áp dụng toàn bảng).
- `status` mặc định `active` khi tạo mới nếu không chỉ định khác.
- Xoá khách hàng luôn là xoá mềm; không có endpoint xoá cứng.

## 10. Phân quyền (RBAC — theo nghiệp vụ, không phải tên class)

| Action | Actor được phép |
|---|---|
| Xem (View) | Actor có `view:customer`; Superuser luôn được phép |
| Tạo (Create) | Actor có `create:customer`; Superuser |
| Sửa (Update) | Actor có `update:customer`; Superuser |
| Xoá (Delete — xoá mềm) | Actor có `delete:customer`; Superuser |
| Xuất dữ liệu (Export) | Quyền đã khai báo (`export:customer`) nhưng **chưa có endpoint sử dụng** trong phạm vi PRD này |

## 11. Yêu cầu phi chức năng (Non-functional, nếu có)

- **Hiệu năng**: danh sách khách hàng phải hỗ trợ phân trang, không trả
  toàn bộ bản ghi trong một response.
- **Toàn vẹn dữ liệu**: `customer_code`/`phone` là định danh nghiệp vụ,
  ràng buộc unique phải được enforce ở cả tầng validation (serializer/form)
  lẫn tầng database (constraint) — validation chỉ là lớp chặn sớm, database
  luôn là lớp chặn cuối.
- **Khả năng mở rộng**: thiết kế field/entity phải đủ ổn định để Order,
  Invoice, Payment ở các sprint sau tham chiếu bằng `Customer.id` mà không
  cần đổi schema.

## 12. Câu hỏi mở / Rủi ro (Open Questions / Risks)

- Có cần endpoint Export (CSV/Excel) trong các sprint gần tới không, hay
  tiếp tục để permission đã khai báo nằm im chờ nhu cầu thực tế?
- Có cần "thùng rác" (trang khôi phục khách hàng đã xoá mềm) trên Dashboard
  giống Product/Category không, hay xoá mềm chỉ cần khôi phục qua Django
  Admin khi thực sự cần?
- Ngưỡng "khách hàng không hoạt động" (`inactive`) hiện là do người dùng tự
  đổi trạng thái thủ công — có cần tự động chuyển trạng thái sau N ngày
  không giao dịch không?

## 13. Bước tiếp theo

- [x] PRD được review & approve bởi: _(retroactive — đã triển khai từ
      2026-07-31)_
- [x] Convert sang prompt kỹ thuật theo [`docs/prompt-features.md`](prompt-features.md)
- [x] Triển khai theo [README.md § Quy tắc Coding & Triển khai](../README.md#quy-tắc-coding--triển-khai)
- [x] Ghi lại kết quả tại [`docs/sprint_2.md`](sprint_2.md)
