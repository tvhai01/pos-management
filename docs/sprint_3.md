# Sprint 3 — Product Management

**Trạng thái:** Hoàn thành
**Ngày hoàn thành:** 2026-08-09

## Mục tiêu

Chuẩn hoá module Product do thành viên trước bàn giao để làm nền dữ liệu an toàn cho Inventory.

## Công việc đã hoàn thành

- Chuẩn hoá Product và Category theo `AuditModel`: UUID, audit fields và soft delete.
- Bổ sung manager mặc định ẩn bản ghi đã xoá và manager audit xem toàn bộ dữ liệu.
- Chuyển toàn bộ thao tác đọc/ghi sang kiến trúc Selector/Service.
- Chuẩn hoá SKU duy nhất, bất biến; Category không bắt buộc.
- Bổ sung validation giá ở nhiều lớp và database constraints.
- Chặn xoá Category đang có Product hoạt động tham chiếu.
- Xây dựng REST API Product/Category với response envelope, search, filter, pagination và RBAC.
- Tích hợp Dashboard session, menu, biểu mẫu, danh sách và thùng rác.
- Chuyển thao tác xoá/khôi phục thành POST; loại bỏ luồng xoá cứng.
- Cập nhật Django Admin để tuân theo xoá mềm.
- Bổ sung migration và tài liệu hợp đồng cho Inventory.

## Quyết định thiết kế

- Inventory liên kết Product bằng UUID, không liên kết bằng SKU.
- SKU dùng để nhận diện nghiệp vụ nhưng không được sửa sau khi tạo.
- Product có thể chưa được gán Category.
- Tên Category và SKU vẫn được giữ duy nhất khi bản ghi đã xoá mềm để tránh nhập nhầm dữ liệu lịch sử.
- Product/Category chỉ xoá mềm; dữ liệu tham chiếu được bảo toàn.

## Kiểm thử

- Bổ sung 29 test cho Product domain, selector, service, API, RBAC và Dashboard.
- Toàn bộ dự án: **142 test passed**.
- Coverage toàn dự án: **87.75%**, đạt yêu cầu tối thiểu 80%.

## Bước tiếp theo

Xây dựng Inventory dựa trên `Product.id`, bao gồm tồn kho hiện tại, phiếu nhập/xuất/điều chỉnh, lịch sử biến động và cơ chế khoá giao dịch khi cập nhật số lượng.
