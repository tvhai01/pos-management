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
- Dashboard UI: trang tổng quan `/reports/` (5 card trong 1 trang, mỗi card
  có bộ lọc riêng — khoảng thời gian độc lập cho từng báo cáo, Top N/sort
  chỉ xuất hiện ở Sản phẩm bán chạy & Khách hàng vì chỉ hai báo cáo đó dùng
  đến) + 5 URL export riêng cho session, dùng lại đúng
  `ReportSelector`/`exports` — không viết lại logic tổng hợp cho transport
  HTML (đúng nguyên tắc "hai transport, cùng Service/Selector" ở README).
  Ban đầu cả 5 card dùng chung 1 `ReportFilterForm`, gây nhầm lẫn vì Top N/
  sort trông như áp dụng cho mọi báo cáo; đã tách thành `ReportDateRangeForm`
  (base) + 5 subclass riêng (`RevenueReportFilterForm`,
  `TopSellingReportFilterForm`, `InventoryReportFilterForm`,
  `PaymentBreakdownReportFilterForm`, `CustomerReportFilterForm`).
  Vòng lặp UX thứ hai (sau phản hồi thực tế dùng thử): mỗi card giờ submit
  filter qua AJAX (`fetch`) vào một `report_*_fragment` view riêng
  (`/reports/<report>/fragment/`, trả về đúng HTML của card đó, không phải
  cả trang) rồi thay `innerHTML` của đúng `<div class="card" id="report-card-
  ...">` — bấm "Lọc" ở 1 card không còn reload cả trang hay đụng đến 4 card
  còn lại (bỏ hẳn cách tiếp cận query-param-có-prefix + hidden input đồng bộ
  giữa các card trước đó, không cần nữa vì không còn share 1 lần submit toàn
  trang). Nút "Xuất CSV" chuyển thành `<button formaction="...export/">` nằm
  trong chính form đó — luôn export đúng giá trị đang gõ trong ô lọc tại thời
  điểm bấm, kể cả khi chưa bấm "Lọc" (trước đó `<a href>` dựng sẵn phía server
  nên xuất ra dữ liệu cũ nếu người dùng gõ filter mới mà quên bấm Lọc trước).
  Input ngày đổi từ `<input type="date">` (định dạng theo locale trình
  duyệt, không ép được dd/mm/yyyy) sang `<input type="text">` hiển thị
  dd/mm/yyyy (`ReportDateRangeForm` nhận cả `"%d/%m/%Y"` lẫn `"%Y-%m-%d"` qua
  `input_formats` để không phá các URL export/insight cũ dùng ISO), có JS
  tự chèn dấu `/` khi gõ. Chart doughnut "Phương thức thanh toán" được bọc
  trong `.chart-container--compact` (max-width cố định) vì Chart.js
  `responsive` không có container giới hạn sẽ phóng to theo bề rộng card.
- `ReportDateRangeForm` (Dashboard) và `ReportDateRangeSerializer` (API) cùng
  gọi chung `apps.reports.validators.resolve_date_range()` để hai transport
  luôn resolve khoảng thời gian mặc định/không hợp lệ giống hệt nhau.
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
- `apps/dashboard/templates/dashboard/reports/index.html` +
  `_revenue_card.html`, `_top_selling_card.html`, `_inventory_card.html`,
  `_payment_card.html`, `_customer_card.html` (mỗi card 1 partial, dùng lại
  cả cho `{% include %}` lần render đầu lẫn cho response của `*_fragment`)
- `docs/prd_report.md`, `docs/sprint_5.md`

**Sửa:**
- `config/settings/base.py` (`LOCAL_APPS` += `apps.reports`)
- `config/urls.py` (include `apps.reports.urls`)
- `config/views.py` (`FEATURE_MODULES` += `reports`)
- `apps/dashboard/views.py` (menu "Báo cáo" + 16 view function: `report_dashboard`,
  5 `report_*_fragment` (AJAX), 5 `report_*_export`, 5 `report_*_insights`)
- `apps/dashboard/urls.py` (16 URL: `report-dashboard` + 5 `*-fragment` +
  5 `*-export` + 5 `*-insights`)
- `apps/dashboard/forms.py` (`ReportDateRangeForm` + 5 per-report subclasses)
- `tests/conftest.py` (fixture RBAC cho `report`: permission/role/client)
- `README.md` (bảng API Dashboard + JSON API cho Report)

## Hướng tích hợp sprint sau

- Trước khi mở rộng Report (cache, giới hạn export, so sánh kỳ), cần một
  quyết định Product Owner chốt các Open Question ở PRD mục 12.
- Bug `order_total_positive` ở `apps/orders/services.py` nên được sửa sớm —
  nó chặn toàn bộ luồng Order/Invoice/Payment thật trên Postgres, không chỉ
  ảnh hưởng test.
