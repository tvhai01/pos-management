# PRD: Quản lý sản phẩm và danh mục (Product Management)

## 1. Thông tin chung
- Module: Product
- Sprint dự kiến: Sprint 1
- Ngày: 2026-08-30
- Trạng thái: Approved

## 2. Bối cảnh & Vấn đề (Problem Statement)
- Vấn đề nghiệp vụ hiện tại là gì? Hệ thống POS cần quản lý danh mục hàng hóa và thông tin sản phẩm chuẩn xác để thu ngân dễ dàng tìm kiếm, chọn mua và xử lý đơn hàng. Hiện tại, việc thiếu một module quản lý sản phẩm đồng bộ khiến việc kiểm soát giá bán, giá nhập và phân loại danh mục gặp khó khăn.
- Vì sao cần giải quyết bây giờ? Đây là module nền tảng cốt lõi (core dependency). Các module khác như Inventory (Kho hàng), Orders (Đơn hàng) và Reports (Báo cáo) bắt buộc phải tham chiếu dữ liệu từ module này .

## 3. Mục tiêu (Goals)
- Mục tiêu 1: Xây dựng hệ thống quản lý danh mục (Category) và sản phẩm (Product) toàn diện cho phép Quản trị viên thêm, sửa, xem, xoá mềm và khôi phục dữ liệu .
- Mục tiêu 2: Đảm bảo tính toàn vẹn dữ liệu: mã SKU duy nhất và bất biến, giá bán (`selling_price`) phải luôn lớn hơn giá nhập (`cost_price`) .
- Mục tiêu 3: Liên kết chặt chẽ với module Kho hàng (Inventory) thông qua định danh UUID của sản phẩm mà không dùng SKU làm khóa ngoại .

## 4. Ngoài phạm vi (Non-goals / Out of Scope)
- Số lượng tồn kho, các nghiệp vụ nhập/xuất/điều chỉnh kho và cảnh báo tồn kho thấp (thuộc phạm vi của module Inventory) .
- Tính năng nhập/xuất dữ liệu hàng loạt từ file Excel/CSV (để dành cho các sprint nâng cấp sau).

## 5. Đối tượng sử dụng (Actors / User Roles)
| Actor | Vai trò trong module này |
|---|---|
| Quản trị viên (Admin / Manager) | Toàn quyền thực hiện các thao tác: Tạo, Xem, Sửa, Xoá mềm, Quản lý Thùng rác và Khôi phục sản phẩm/danh mục . |
| Nhân viên bán hàng (Staff) | Tra cứu, tìm kiếm sản phẩm và xem thông tin chi tiết phục vụ cho nghiệp vụ bán hàng . |

## 6. Entity nghiệp vụ
### Category (Danh mục)
| Field | Bắt buộc? | Unique? | Ghi chú |
|---|---|---|---|
| id | Có | Có | UUID định danh duy nhất |
| name | Có | Có | Tên danh mục, tối đa 100 ký tự  |
| description | Không | Không | Mô tả chi tiết về danh mục |
| created_at / updated_at | Có | Không | Thời gian tạo và cập nhật bản ghi |
| created_by / updated_by | Không | Không | Người thực hiện thao tác |
| is_deleted / deleted_at | Có | Không | Trạng thái xoá mềm và thời điểm xoá mềm |

### Product (Sản phẩm)
| Field | Bắt buộc? | Unique? | Ghi chú |
|---|---|---|---|
| id | Có | Có | UUID định danh duy nhất |
| sku | Có | Có | Mã SKU chuẩn hóa chữ hoa, bất biến (không được sửa sau khi khởi tạo)  |
| name | Có | Không | Tên sản phẩm  |
| description | Không | Không | Mô tả chi tiết sản phẩm |
| image | Không | Không | Đường dẫn hình ảnh sản phẩm |
| category | Không | Không | Liên kết đến Category (quan hệ khóa ngoại PROTECT)  |
| unit | Có | Không | Đơn vị tính (vd: cái, hộp, ly, kg...)  |
| cost_price | Có | Không | Giá nhập (số thập phân dương)  |
| selling_price | Có | Không | Giá bán (số thập phân dương, phải lớn hơn cost_price)  |
| status | Có | Không | Trạng thái hoạt động (`active` hoặc `inactive`)  |
| created_at / updated_at | Có | Không | Thời gian tạo và cập nhật bản ghi |
| created_by / updated_by | Không | Không | Người thực hiện thao tác |
| is_deleted / deleted_at | Có | Không | Trạng thái xoá mềm và thời điểm xoá mềm |

### Trạng thái (Status)
| Giá trị | Ý nghĩa | Chuyển từ trạng thái nào |
|---|---|---|
| active | Sản phẩm đang kinh doanh bình thường | (trạng thái khởi tạo) |
| inactive | Sản phẩm tạm ngừng kinh doanh | active |

## 7. Quan hệ với module khác (Dependencies)
- Product tham chiếu tới Category qua quan hệ khóa ngoại (với ràng buộc `PROTECT`) .
- Inventory (Kho hàng) tham chiếu tới `Product.id` bằng khóa ngoại với ràng buộc `PROTECT` .
- Hệ thống áp dụng **Soft Delete** cho cả Product và Category để bảo toàn lịch sử giao dịch của đơn hàng và kho hàng . Không cho phép xóa cứng hoặc xóa danh mục khi vẫn còn sản phẩm hoạt động tham chiếu đến .

## 8. Chức năng (Functional Requirements)
### FR-1: Quản lý danh sách Sản phẩm & Danh mục
- Mô tả: Người dùng xem danh sách sản phẩm và danh mục, hỗ trợ tìm kiếm nhanh, lọc theo trạng thái/danh mục và phân trang .
- Acceptance Criteria:
  - [ ] Cho phép tìm kiếm theo SKU, tên sản phẩm hoặc mô tả .
  - [ ] Cho phép lọc danh sách theo danh mục (Category) và trạng thái (`active`/`inactive`) .
  - [ ] Danh sách kết quả bắt buộc hỗ trợ phân trang (Pagination) .
  - [ ] Giao diện danh sách mặc định ẩn các bản ghi đã bị xoá mềm (`is_deleted = True`) .
  - [ ] Trường hợp lỗi: Hiển thị thông báo phù hợp khi không tìm thấy dữ liệu.

### FR-2: Thêm mới Sản phẩm & Danh mục (Create)
- Mô tả: Quản trị viên khởi tạo mới bản ghi sản phẩm hoặc danh mục vào hệ thống .
- Acceptance Criteria:
  - [ ] Kiểm tra tính duy nhất của mã SKU và tên Category (kiểm tra cả các bản ghi đang nằm trong thùng rác) .
  - [ ] Đảm bảo giá bán (`selling_price`) lớn hơn giá nhập (`cost_price`) .
  - [ ] Tự động chuẩn hóa mã SKU thành chữ hoa ngay khi tạo .
  - [ ] Trường hợp lỗi: Trả về lỗi chi tiết nếu bỏ trống trường bắt buộc, trùng SKU hoặc giá nhập/bán không hợp lệ.

### FR-3: Cập nhật thông tin Sản phẩm & Danh mục (Update)
- Mô tả: Quản trị viên cập nhật các thông tin chi tiết của sản phẩm hoặc danh mục .
- Acceptance Criteria:
  - [ ] Cho phép chỉnh sửa các trường thông tin như tên, mô tả, hình ảnh, đơn vị, giá nhập, giá bán, trạng thái, danh mục .
  - [ ] **Tuyệt đối không** cho phép chỉnh sửa trường `sku` sau khi sản phẩm đã được tạo thành công .
  - [ ] Trường hợp lỗi: Báo lỗi nếu vi phạm ràng buộc giá hoặc cố tình thay đổi mã SKU cố định.

### FR-4: Xoá mềm & Khôi phục (Delete & Restore)
- Mô tả: Quản trị viên thực hiện xoá mềm sản phẩm hoặc danh mục, hoặc khôi phục lại từ thùng rác .
- Acceptance Criteria:
  - [ ] Thực hiện đánh dấu xoá mềm (`is_deleted = True`, ghi nhận `deleted_at`) thay vì xoá vĩnh viễn khỏi cơ sở dữ liệu .
  - [ ] Chặn hành động xóa danh mục (Category) nếu vẫn còn sản phẩm đang hoạt động tham chiếu đến danh mục đó .
  - [ ] Hỗ trợ xem khu vực thùng rác và khôi phục bản ghi (Product chỉ được khôi phục nếu Category liên quan đang hoạt động) .

## 9. Quy tắc nghiệp vụ & Validation
- SKU và Tên Category phải là duy nhất trên toàn hệ thống, bao gồm cả các bản ghi đang nằm trong thùng rác .
- SKU là mã định danh bất biến (Immutable), không được phép sửa đổi sau khi khởi tạo .
- Giá bán (`selling_price`) bắt buộc phải lớn hơn giá nhập (`cost_price`) .
- Các module phụ thuộc (như Inventory) chỉ liên kết tới Product thông qua `Product.id` (UUID), tuyệt đối không dùng SKU làm khóa liên kết .
- Mọi thao tác ghi dữ liệu (Create, Update, Delete) phải đi qua Service Layer để đảm bảo tính toàn vẹn và ghi log audit .

## 10. Phân quyền (RBAC — theo nghiệp vụ)
| Action | Actor được phép |
|---|---|
| Xem danh sách / Chi tiết (View) | Quản trị viên, Nhân viên bán hàng  |
| Tạo mới (Create) | Quản trị viên  |
| Cập nhật (Update) | Quản trị viên  |
| Xoá mềm / Khôi phục (Delete / Restore) | Quản trị viên  |

## 11. Yêu cầu phi chức năng (Non-functional)
- Hiệu năng: Danh sách sản phẩm hỗ trợ phân trang tối ưu, thời gian phản hồi truy vấn tìm kiếm dưới 500ms.
- Bảo mật: Các thao tác thay đổi dữ liệu yêu cầu kiểm tra quyền hạn chặt chẽ qua cơ chế phân quyền RBAC (HasPermission / require_permission) .

## 12. Câu hỏi mở / Rủi ro (Open Questions / Risks)
- Không có rủi ro lớn; các quy tắc ràng buộc quan hệ `PROTECT` và kiểm tra logic giá đã được thiết kế đồng bộ với kiến trúc dự án.

## 13. Bước tiếp theo
- [ ] PRD được review & approve bởi: Product Owner / Tech Lead
- [ ] Convert sang prompt kỹ thuật theo `docs/prompt-features.md` 
- [ ] Triển khai theo quy tắc coding của dự án tại `README.md` 
- [ ] Ghi lại kết quả tại `docs/sprint_1.md` 