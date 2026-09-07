# Sprint 5 — Report Module

**Trạng thái:** Hoàn thành (một phần — xem "Chưa làm / để mở" bên dưới)
**Ngày hoàn thành:** 2026-09-07

## Mục tiêu

Hiện thực hoá module Báo cáo (Report) theo [`docs/prd_report.md`](prd_report.md):
tổng hợp read-only dữ liệu đã có của Invoice/Order/Payment/Inventory/Product/
Customer thành 5 loại báo cáo (doanh thu, sản phẩm bán chạy, tồn kho, phương
thức thanh toán, khách hàng), cho phép xuất CSV, và hiện thực hoá resource
`report` đã được đặt sẵn trong RBAC từ Sprint 1 nhưng chưa dùng tới.

## Công việc đã hoàn thành

- Tạo app `apps/reports/` — không có model/entity riêng (đúng PRD mục 6):
  `constants.py`, `permissions.py`, `selectors.py` (5 method tổng hợp dùng
  `annotate`/`aggregate`, không load record về Python để cộng tay),
  `serializers.py` (chỉ validate input query param — không có output
  serializer vì kết quả là dict tổng hợp, không phải ORM instance),
  `exports.py` (format CSV + `build_csv_response` dùng chung cho cả API và
  Dashboard), `views.py` (10 view: 5 report + 5 export, đều là `APIView`
  thuần, không có Service layer vì Report không ghi dữ liệu gì).
- 10 endpoint JSON API dưới `/api/v1/reports/...` (xem README mục "Báo cáo").
- Dashboard UI: trang tổng quan `/reports/` (5 section trong 1 trang, bộ lọc
  khoảng thời gian/Top N/sort dùng chung) + 5 URL export riêng cho session,
  dùng lại đúng `ReportSelector`/`exports` — không viết lại logic tổng hợp
  cho transport HTML (đúng nguyên tắc "hai transport, cùng Service/Selector"
  ở README).
- `ReportFilterForm` (Dashboard) và `ReportDateRangeSerializer` (API) cùng gọi
  chung `apps.reports.validators.resolve_date_range()` để hai transport luôn
  resolve khoảng thời gian mặc định/không hợp lệ giống hệt nhau.
- RBAC: `view:report`, `export:report` — khai báo trong
  `apps/reports/permissions.py`, tham chiếu `PermissionResource.REPORT` có
  sẵn từ Sprint 1. Không sửa gì trong `apps/accounts`.
- Cập nhật `README.md` (bảng API Dashboard + JSON API cho Report) và
  `config/views.py::FEATURE_MODULES`.
- 50 test mới cho `apps/reports/` (selector, permission, validation, export
  CSV, dashboard) — coverage riêng module: **100%**.

## Quyết định thiết kế

- **Nguồn doanh thu = `Invoice.status = Paid`**, không phải Order hay Payment
  (PRD mục 9): Order có thể "Paid" mà chưa có Invoice hợp lệ; một Invoice có
  thể có nhiều `Payment`/`PaymentTransaction` (retry sau khi thất bại) nên
  cộng theo Payment dễ đếm trùng. Đây vẫn là Open Question trong PRD (mục 12)
  — **chưa được ai duyệt chính thức**, cần Product Owner/giảng viên xác nhận.
- Không có Service layer cho Report — không có thao tác ghi nào cần điều
  phối (README mục 1).
- Sản phẩm/khách hàng đã xoá mềm vẫn xuất hiện đúng trong báo cáo lịch sử
  (dùng snapshot `OrderItem.product_sku`/`product_name`, và join trực tiếp
  qua `customer__...` trong `.values()` — không đi qua manager loại trừ
  soft-delete của Customer).
- `resolve_date_range()` là một hàm dùng chung duy nhất (không phải class),
  đặt tại `apps/reports/validators.py`, được cả Serializer và Form gọi —
  cùng pattern với `apps.customers.validators` đã dùng ở Sprint 2.

## Chưa làm / để mở (theo yêu cầu "chỗ nào chưa chắc chắn thì đừng làm")

PRD mục 12 (Open Questions) liệt kê 5 điểm chưa chốt. Sprint này **cố tình
không cài đặt** các phần phụ thuộc vào quyết định chưa có, để tránh đoán mò
kiến trúc thay Product Owner:

- **Không cache kết quả báo cáo** (Redis) — TTL chưa được chốt cụ thể là bao
  nhiêu phút. NFR trong PRD chỉ nói "có thể cache", không bắt buộc.
- **Không giới hạn khoảng thời gian tối đa** cho filter — PRD chưa chốt giới
  hạn xa nhất; giữ nguyên "không giới hạn" như AC gốc của FR-1.
- **Không giới hạn số dòng tối đa khi export CSV** — PRD chưa chốt con số cụ
  thể.
- **Không có báo cáo theo nhân viên bán hàng** — đã là Non-goal tường minh
  trong PRD (mục 4), không thuộc phạm vi sprint này.
- **So sánh kỳ này với kỳ trước** (+X% so với tháng trước) — Non-goal trong
  PRD, không cài đặt.

Không có cái nào trong số này chặn việc dùng Report ở mức MVP hiện tại; chúng
chỉ là polish/scale-up cần một quyết định nghiệp vụ trước khi làm.

## Phát hiện ngoài phạm vi — bug có sẵn, KHÔNG do Sprint 5 gây ra

Trong lúc viết test cho Report (cần tạo Order/Invoice/Payment mẫu), phát hiện
`apps.orders.services.OrderService.create_order` **không thể tạo được Order
nào trên PostgreSQL**: nó `Order.objects.create(..., total_amount=Decimal("0"))`
trước rồi mới tính tổng thật và `save()` lại sau, nhưng `Order` có
`CheckConstraint` `order_total_positive` (`total_amount > 0`) — INSERT ban
đầu với `total_amount=0` luôn vi phạm constraint này ngay lập tức.

Đã tái hiện với chính test có sẵn của module đó
(`apps/orders/tests/test_order_flow.py::test_existing_product_flows_to_order_invoice_and_payment`)
— test này **fail 100%** trên Postgres thật với cùng lỗi
`IntegrityError: ... violates check constraint "order_total_positive"`,
xác nhận đây là lỗi có sẵn từ commit `477867f` ("UPDATE INVOICE, ORDER,
PAYMENT"), không liên quan đến Report và **không được sửa trong sprint này**
(ngoài phạm vi được giao). Vì lỗi này, test của Report tạo Order/Invoice/
Payment mẫu trực tiếp qua ORM (bỏ qua `OrderService.create_order`) thay vì
gọi service đó — xem docstring đầu file `apps/reports/tests/test_selectors.py`.

**Cần dev phụ trách Order xử lý trước khi module Order dùng được thật** (vd.
tính `total_amount` xong rồi mới `Order.objects.create()`, thay vì tạo trước
với giá trị 0 rồi update sau).

## Kiểm thử

- Bổ sung 50 test cho `apps/reports/` (15 selector, 28 view API, 6 dashboard,
  1 export nội dung CSV chi tiết) — coverage riêng module: **100%**
  (`selectors.py`, `views.py`, `exports.py`, `serializers.py`,
  `validators.py`, `permissions.py`, `constants.py` đều 100%).
- Toàn dự án: **226 passed, 1 failed** (thất bại duy nhất là bug có sẵn ở
  `apps/orders` nêu trên, không liên quan Report).
- Coverage toàn dự án: **82.59%**, đạt yêu cầu tối thiểu 80%.
- `black --check` và `ruff check` sạch cho toàn bộ file mới/sửa trong sprint
  này (`apps/reports/`, `apps/dashboard/views.py`, `forms.py`, `urls.py`).
  `mypy apps/reports/` không phát sinh lỗi mới (các lỗi còn lại đều pre-existing
  ở `apps/accounts`, `config/settings/development.py`, ngoài phạm vi sprint).

## Files Changed

**Mới:**
- `apps/reports/` (toàn bộ: `apps.py`, `constants.py`, `permissions.py`,
  `selectors.py`, `serializers.py`, `exports.py`, `views.py`, `urls.py`,
  `validators.py`, `migrations/__init__.py`, `tests/`)
- `apps/dashboard/templates/dashboard/reports/index.html`
- `docs/prd_report.md`, `docs/sprint_5.md`

**Sửa:**
- `config/settings/base.py` (`LOCAL_APPS` += `apps.reports`)
- `config/urls.py` (include `apps.reports.urls`)
- `config/views.py` (`FEATURE_MODULES` += `reports`)
- `apps/dashboard/views.py` (menu "Báo cáo" + 6 view function mới)
- `apps/dashboard/urls.py` (6 URL mới)
- `apps/dashboard/forms.py` (`ReportFilterForm`)
- `tests/conftest.py` (fixture RBAC cho `report`: permission/role/client)
- `README.md` (bảng API Dashboard + JSON API cho Report)

## Hướng tích hợp sprint sau

- Trước khi mở rộng Report (cache, giới hạn export, so sánh kỳ), cần một
  quyết định Product Owner chốt các Open Question ở PRD mục 12.
- Bug `order_total_positive` ở `apps/orders/services.py` nên được sửa sớm —
  nó chặn toàn bộ luồng Order/Invoice/Payment thật trên Postgres, không chỉ
  ảnh hưởng test.
