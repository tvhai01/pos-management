# PRD — Inventory Management

## 1. Mục tiêu

Inventory Management quản lý số lượng tồn hiện tại của từng Product và lưu lịch sử mọi lần nhập, xuất hoặc điều chỉnh. Dữ liệu tồn kho phải nhất quán khi nhiều yêu cầu cập nhật đồng thời và không được phép âm.

## 2. Phạm vi và tác nhân

- **System Admin/Manager**: xem tồn kho, cập nhật ngưỡng tồn thấp và thực hiện nghiệp vụ kho theo RBAC.
- **Nhân viên kho**: xem tồn và tạo phiếu nhập/xuất nếu được cấp quyền.
- **Order/Invoice trong sprint sau**: gọi Inventory Service để trừ/hoàn tồn, không sửa trực tiếp model.

Phiên bản này quản lý một kho tổng. Quản lý nhiều chi nhánh/kho vật lý nằm ngoài phạm vi.

## 3. Mô hình dữ liệu

### Inventory

- `id`: UUID.
- `product`: quan hệ một-một đến `Product.id`, dùng `PROTECT`.
- `quantity`: số lượng tồn hiện tại, tối thiểu 0, tối đa 3 chữ số thập phân.
- `low_stock_threshold`: ngưỡng cảnh báo tồn thấp, tối thiểu 0.
- `created_at`, `updated_at`, `created_by`, `updated_by`: trường audit.

Inventory không bị xoá. Product chỉ bị xoá mềm nên dữ liệu tồn và lịch sử vẫn được bảo toàn.

### StockMovement

- `id`: UUID.
- `inventory`: khoá ngoại đến Inventory, dùng `PROTECT`.
- `movement_type`: `inbound`, `outbound` hoặc `adjustment`.
- `quantity_delta`: lượng thay đổi có dấu.
- `balance_before`, `balance_after`: tồn trước và sau giao dịch.
- `reference_code`: mã chứng từ/tham chiếu không bắt buộc.
- `note`: ghi chú không bắt buộc.
- `created_at`, `created_by`: nguồn audit chính; bản ghi là bất biến.

## 4. Business rules

1. Mỗi Product có tối đa một Inventory và được liên kết bằng UUID, không liên kết bằng SKU.
2. Không cập nhật `Inventory.quantity` trực tiếp ngoài Inventory Service.
3. Mọi thay đổi số lượng phải tạo StockMovement trong cùng một database transaction.
4. Khi cập nhật tồn, Service khoá Product/Inventory bằng `select_for_update()` để tránh lost update.
5. Số lượng nhập/xuất phải lớn hơn 0; xuất kho không được làm tồn âm.
6. Điều chỉnh nhận **số tồn mục tiêu** lớn hơn hoặc bằng 0; hệ thống tự tính phần chênh lệch.
7. Không tạo giao dịch điều chỉnh nếu số tồn mục tiêu bằng số tồn hiện tại.
8. `inbound` luôn có delta dương, `outbound` luôn có delta âm; StockMovement không được sửa hoặc xoá.
9. Product đã xoá mềm không được phát sinh giao dịch kho mới nhưng lịch sử cũ vẫn xem được.
10. Tồn thấp khi `0 < quantity <= low_stock_threshold`; hết hàng khi `quantity = 0`.

## 5. Chức năng

- Danh sách tồn kho có tìm kiếm Product, lọc Category/trạng thái Product và phân trang.
- Xem tồn hiện tại, trạng thái tồn và lịch sử biến động của một Product.
- Nhập kho, xuất kho và điều chỉnh số tồn.
- Cập nhật ngưỡng cảnh báo tồn thấp.
- Lọc/tìm kiếm/phân trang lịch sử biến động.
- REST API dùng JWT và Dashboard dùng session.

## 6. Phân quyền

- `view:inventory`: xem danh sách, chi tiết và lịch sử.
- `create:inventory`: tạo giao dịch nhập/xuất/điều chỉnh.
- `update:inventory`: cập nhật ngưỡng tồn thấp.
- Superuser được phép thực hiện mọi thao tác.

Không cung cấp thao tác xoá Inventory hoặc StockMovement.

## 7. API dự kiến

| Method | Endpoint | Mục đích |
|---|---|---|
| `GET` | `/api/v1/inventory/` | Danh sách tồn kho |
| `GET` | `/api/v1/inventory/{product_id}/` | Chi tiết tồn theo Product |
| `PATCH` | `/api/v1/inventory/{product_id}/threshold/` | Cập nhật ngưỡng tồn thấp |
| `GET` | `/api/v1/inventory/movements/` | Lịch sử biến động |
| `POST` | `/api/v1/inventory/movements/` | Nhập/xuất/điều chỉnh tồn |

## 8. Tiêu chí nghiệm thu

- Model dùng UUID/audit fields và có database constraints chống tồn âm/sai dấu giao dịch.
- Mọi thao tác ghi đi qua Service, mọi truy vấn đi qua Selector.
- Giao dịch kho dùng transaction và row lock.
- API/Dashboard áp dụng RBAC đúng resource Inventory.
- Search, filter, ordering và pagination hoạt động.
- Có test cho nhập, xuất, điều chỉnh, không đủ tồn, Product đã xoá, audit, API, RBAC và Dashboard.
- Toàn bộ test dự án pass và coverage không thấp hơn 80%.

## 9. Ngoài phạm vi

- Nhiều kho/chi nhánh, chuyển kho, lô hàng, hạn sử dụng, số serial.
- Giá vốn bình quân/FIFO.
- Import/export CSV và quy trình duyệt phiếu kho.
