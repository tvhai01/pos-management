# PRD — Product Management

## 1. Mục tiêu

Product Management cung cấp dữ liệu sản phẩm và danh mục ổn định cho các module bán hàng và Inventory. Module cho phép quản trị sản phẩm, danh mục, trạng thái kinh doanh và lịch sử người tạo/cập nhật mà không làm mất dữ liệu đã được tham chiếu.

## 2. Phạm vi và tác nhân

- **System Admin/Manager**: xem, tạo, sửa và xoá mềm Product/Category theo quyền RBAC.
- **Nhân viên có quyền xem**: tìm kiếm, lọc và xem danh sách.
- **Inventory**: liên kết tồn kho bằng UUID của Product; không dùng SKU làm khoá ngoại.

## 3. Mô hình dữ liệu

### Category

- `id`: UUID.
- `name`: bắt buộc, duy nhất, tối đa 100 ký tự.
- `description`: không bắt buộc.
- `created_at`, `updated_at`, `created_by`, `updated_by`: trường audit.
- `is_deleted`, `deleted_at`: xoá mềm.

### Product

- `id`: UUID.
- `sku`: bắt buộc, duy nhất, chuẩn hoá chữ hoa và không được sửa sau khi tạo.
- `name`: bắt buộc.
- `description`, `image`: không bắt buộc.
- `category`: không bắt buộc, liên kết Category bằng `PROTECT`.
- `unit`: một trong các đơn vị được hệ thống hỗ trợ.
- `cost_price`, `selling_price`: số thập phân dương; giá bán phải lớn hơn giá nhập.
- `status`: `active` hoặc `inactive`.
- `created_at`, `updated_at`, `created_by`, `updated_by`: trường audit.
- `is_deleted`, `deleted_at`: xoá mềm.

## 4. Business rules

1. SKU và tên Category không được trùng, kể cả với bản ghi đang nằm trong thùng rác.
2. SKU là định danh nghiệp vụ bất biến; các module khác liên kết bằng UUID của Product.
3. Không xoá cứng Product hoặc Category qua ứng dụng.
4. Không được xoá Category khi còn Product chưa bị xoá mềm tham chiếu đến Category đó.
5. Product có thể không thuộc Category.
6. Product chỉ được khôi phục nếu Category liên quan (nếu có) vẫn đang hoạt động.
7. Mọi thao tác ghi phải đi qua Service và ghi nhận người tạo/cập nhật.
8. Danh sách mặc định không hiển thị bản ghi đã xoá mềm.

## 5. Chức năng

- Danh sách Product có tìm kiếm theo SKU/tên/mô tả, lọc Category/trạng thái và phân trang.
- Tạo, xem chi tiết, cập nhật và xoá mềm Product qua REST API/Dashboard; khôi phục qua thùng rác Dashboard.
- Danh sách Category có tìm kiếm và phân trang.
- Tạo, xem chi tiết, cập nhật và xoá mềm Category qua REST API/Dashboard; khôi phục qua thùng rác Dashboard.
- Cung cấp cả Dashboard sử dụng session và REST API theo response envelope chung.

## 6. Phân quyền

Sử dụng các quyền `view`, `create`, `update`, `delete` cho hai resource `product` và `category`. API dùng `HasPermission`; Dashboard dùng `require_permission`. Superuser được phép thực hiện mọi thao tác.

## 7. Tiêu chí nghiệm thu

- Model dùng UUID, audit fields và soft delete theo quy tắc dự án.
- API và Dashboard không cho truy cập trái quyền.
- Giá và quan hệ giá được kiểm tra ở serializer/form, service và database constraint.
- SKU không thể sửa sau khi tạo.
- Không thể xoá Category đang được Product hoạt động tham chiếu.
- Search, filter và pagination hoạt động trên danh sách chính thức.
- Unit test bao phủ model, selector, service, API, RBAC và Dashboard.

## 8. Ngoài phạm vi

- Số lượng tồn, nhập/xuất/điều chỉnh kho và cảnh báo tồn thấp thuộc module Inventory.
- Import/export CSV và quản lý nhiều kho chưa nằm trong sprint này.

## 9. Hợp đồng với Inventory

Inventory phải tham chiếu `Product.id` bằng khoá ngoại `PROTECT`. Inventory không cập nhật trực tiếp Product và không lưu SKU như khoá liên kết. Product đã có giao dịch kho chỉ được xoá mềm để bảo toàn lịch sử.
