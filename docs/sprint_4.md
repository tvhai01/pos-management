# Sprint 4 — Inventory Management

**Trạng thái:** Hoàn thành
**Ngày hoàn thành:** 2026-08-09

## Mục tiêu

Xây dựng module quản lý tồn kho an toàn trên nền Product UUID, có lịch sử nhập/xuất/điều chỉnh và chống sai số lượng khi nhiều giao dịch xảy ra đồng thời.

## Công việc đã hoàn thành

- Bổ sung Inventory một-một với Product và StockMovement bất biến.
- Khởi tạo tồn bằng 0 cho Product hiện có qua data migration và Product mới qua Service.
- Hỗ trợ số lượng tối đa 3 chữ số thập phân cho cả sản phẩm đếm chiếc và cân/đong.
- Bổ sung database constraints chống tồn âm, ngưỡng âm, delta bằng 0 và sai dấu giao dịch.
- Cài đặt nhập kho, xuất kho và điều chỉnh số tồn mục tiêu.
- Mỗi giao dịch cập nhật balance và tạo lịch sử trong cùng transaction.
- Khoá Product/Inventory bằng `select_for_update()` trước khi thay đổi số lượng.
- Chặn xuất vượt tồn, giao dịch Product đã xoá và điều chỉnh không làm thay đổi số tồn.
- Bổ sung Selector, Service, Serializer, API, RBAC và response envelope theo rule dự án.
- Tích hợp Dashboard danh sách tồn, bộ lọc, chi tiết, lịch sử, form giao dịch và ngưỡng tồn thấp.
- Cập nhật Django Admin theo hướng chỉ đọc số tồn/lịch sử, không cho sửa hoặc xoá trực tiếp.
- Cập nhật API root, README và PRD Inventory.

## Quyết định thiết kế

- Sprint này quản lý một kho tổng; chưa tạo Warehouse vì chưa có yêu cầu nhiều chi nhánh.
- `Product.id` là khoá liên kết ổn định; SKU chỉ dùng để tìm kiếm/hiển thị.
- `Inventory.quantity` là snapshot để đọc nhanh; StockMovement là sổ lịch sử để kiểm toán.
- `quantity` của adjustment là số tồn mục tiêu, hệ thống tự tính delta.
- Không cung cấp delete cho Inventory hoặc StockMovement.

## Kiểm thử

- Bổ sung 29 test Inventory.
- Toàn bộ dự án: **171 test passed**.
- Coverage toàn dự án: **88.88%**, đạt yêu cầu tối thiểu 80%.
- Inventory API views: **100%**; Inventory Service: **96.97%**.

## Hướng tích hợp sprint sau

Order/Invoice phải gọi `InventoryService.record_movement()` để trừ hoặc hoàn tồn. Không được cập nhật trực tiếp `Inventory.quantity` và không tự tạo StockMovement bên ngoài Service.
