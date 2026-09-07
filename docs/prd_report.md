    # PRD: Report Management (Báo cáo)

## 1. Thông tin chung
- Module: Report
- Sprint dự kiến: 5 (sau Inventory Management — Sprint 4)
- Người viết PRD: huynt
- Ngày: 2026-09-07
- Trạng thái: Draft

## 2. Bối cảnh & Vấn đề (Problem Statement)

Sau Sprint 1-4, hệ thống đã có đủ dữ liệu nghiệp vụ cốt lõi: khách hàng
(Customer), sản phẩm & tồn kho (Product/Inventory), và — theo commit gần nhất —
đơn hàng, hoá đơn, thanh toán (Order/Invoice/Payment). Tuy nhiên **không có nơi
nào để xem lại dữ liệu này ở mức tổng hợp**: Quản lý hiện phải tự vào từng
danh sách (đơn hàng, hoá đơn, tồn kho...) và cộng dồn thủ công để biết doanh
thu hôm nay là bao nhiêu, sản phẩm nào bán chạy, hay sản phẩm nào sắp hết
hàng cần nhập thêm.

Hệ thống phân quyền (RBAC) đã đặt sẵn resource `report`
(`apps/accounts/constants.py::PermissionResource.REPORT`) từ Sprint 1 nhưng
chưa có permission nào được seed cho resource này và chưa có module nào dùng
tới — đây là module đầu tiên hiện thực hoá resource đó.

Cần giải quyết bây giờ vì đây là module cuối cùng "khép vòng" dữ liệu của các
sprint trước — không có nó, dữ liệu Order/Invoice/Payment/Inventory thu thập
được không tạo ra giá trị quan sát/ra quyết định nào cho người quản lý.

## 3. Mục tiêu (Goals)

- Mục tiêu 1: Quản lý xem được **doanh thu** theo khoảng thời gian tuỳ chọn
  (tổng tiền, số hoá đơn, giá trị trung bình/hoá đơn) mà không cần cộng thủ
  công.
- Mục tiêu 2: Quản lý xác định được **sản phẩm bán chạy** và **sản phẩm sắp
  hết/hết hàng** để ra quyết định nhập hàng.
- Mục tiêu 3: Quản lý xem được **hiệu quả thu tiền theo phương thức thanh
  toán** (QR/SePay vs. thủ công, tỉ lệ thành công/thất bại).
- Mục tiêu 4: Toàn bộ báo cáo **xuất được ra CSV** để lưu trữ hoặc xử lý tiếp
  ở công cụ khác (Excel...).
- Mục tiêu 5 (đo lường được): mọi báo cáo trả kết quả trong dưới 3 giây với
  dữ liệu 1 năm hoạt động ở quy mô một cửa hàng (hàng chục nghìn Order/Invoice).

## 4. Ngoài phạm vi (Non-goals / Out of Scope)

- **Report builder tuỳ biến** (người dùng tự chọn field/tự tạo biểu đồ) — chỉ
  có các báo cáo được định nghĩa sẵn trong PRD này.
- **Xuất PDF** hoặc file có định dạng trình bày đẹp — chỉ CSV cho sprint này.
- **Lên lịch gửi báo cáo qua email** (scheduled report) — để dành sprint sau
  nếu có nhu cầu.
- **Báo cáo theo nhân viên bán hàng** (doanh số của từng user tạo đơn) — Order
  hiện có `created_by` (audit field) nhưng dùng field này làm "người bán hàng"
  là quyết định nghiệp vụ cần chốt riêng, xem mục 12 Open Questions.
- **Đa chi nhánh/đa kho** — kế thừa giới hạn "một kho tổng" của Inventory
  Management (`docs/prd_inventory.md`), không tổng hợp theo chi nhánh.
- **Đa tiền tệ** — giả định toàn bộ giao dịch dùng `VND` (mặc định hiện tại
  của Order/Invoice/Payment); báo cáo không quy đổi tỉ giá.
- **Lưu lịch sử các lần xem/xuất báo cáo** (audit log riêng cho report) —
  không tạo entity/bảng mới cho việc này ở sprint này.
- **So sánh kỳ này với kỳ trước** (vd. "+12% so với tháng trước") — chỉ hiển
  thị số liệu của kỳ đang chọn.

## 5. Đối tượng sử dụng (Actors / User Roles)

| Actor | Vai trò trong module này |
|---|---|
| Quản lý (Manager) | Xem toàn bộ báo cáo, chọn khoảng thời gian, xuất CSV |
| Nhân viên bán hàng | Không có quyền xem báo cáo mặc định (dữ liệu doanh thu/lợi nhuận là thông tin nhạy cảm) — có thể được Quản lý cấp quyền `view:report` riêng nếu cần |
| Superuser | Toàn quyền, bypass RBAC như mọi module khác |

## 6. Entity nghiệp vụ

Report **không tạo entity/bảng dữ liệu mới**. Đây là lớp tổng hợp (aggregate),
chỉ đọc (read-only) trên dữ liệu đã có của các module khác:

| Nguồn dữ liệu | Field liên quan dùng cho báo cáo |
|---|---|
| `Invoice` (invoices) | `status`, `total_amount`, `paid_at`, `created_at`, `customer` |
| `Order` + `OrderItem` (orders) | `status`, `created_at`; `product_name`, `product_sku`, `quantity`, `total_amount` (snapshot tại thời điểm bán, không phụ thuộc Product hiện tại) |
| `Payment` + `PaymentTransaction` (payments) | `status`, `amount`, `payment_method`, `provider`, `processed_at` |
| `Inventory` + `StockMovement` (inventory) | `quantity`, `low_stock_threshold`, `movement_type`, `quantity_delta`, `created_at` |
| `Product` (product) | `sku`, `name`, `cost_price`, `selling_price`, `category`, `status` |
| `Customer` (customers) | `customer_code`, `full_name`, `created_at` |

Vì không có entity mới nên không có mục Trạng thái (Status) riêng cho module
này.

## 7. Quan hệ với module khác (Dependencies)

- Report **chỉ đọc** (read-only) từ `customers`, `product`, `inventory`,
  `orders`, `invoices`, `payments` — không ghi, không thêm FK từ các module đó
  trỏ về Report (chiều phụ thuộc chỉ một chiều: Report → các module khác).
- Report không làm thay đổi hành vi của bất kỳ module nào ở trên; các module
  đó không cần biết Report tồn tại.
- Dữ liệu Product/Category đã bị xoá mềm **vẫn phải xuất hiện đầy đủ** trong
  báo cáo lịch sử (vd. sản phẩm bán chạy tháng trước dù nay đã ngừng kinh
  doanh) — báo cáo dùng dữ liệu snapshot đã lưu sẵn trên `OrderItem`
  (`product_name`, `product_sku`) chứ không phụ thuộc bản ghi `Product` hiện
  tại còn tồn tại hay không.
- Không cần Soft Delete cho Report vì không có entity nào được tạo ra.

## 8. Chức năng (Functional Requirements)

### FR-1: Báo cáo doanh thu (Revenue Report)
- Mô tả: Quản lý chọn khoảng thời gian (from–to), xem tổng doanh thu, tổng số
  hoá đơn đã thanh toán, giá trị trung bình/hoá đơn, và biểu đồ/bảng doanh thu
  theo ngày (hoặc theo tuần/tháng nếu khoảng thời gian dài).
- Acceptance Criteria:
  - [ ] Doanh thu chỉ tính trên Invoice ở trạng thái `Paid` (không tính
        `Draft`, `Pending payment`, `Cancelled`) — xem Quy tắc nghiệp vụ.
  - [ ] Mặc định hiển thị 30 ngày gần nhất nếu không chọn khoảng thời gian.
  - [ ] Cho phép chọn khoảng thời gian tuỳ ý trong quá khứ (không giới hạn xa
        bao nhiêu, nhưng xem NFR về hiệu năng).
  - [ ] Kết quả nhóm theo ngày khi khoảng thời gian ≤ 31 ngày, theo tuần khi
        ≤ 180 ngày, theo tháng khi dài hơn.
  - [ ] Trường hợp lỗi: chọn `from` sau `to` → báo lỗi validation, không trả
        dữ liệu rỗng âm thầm.

### FR-2: Báo cáo sản phẩm bán chạy (Top-selling Products)
- Mô tả: Quản lý xem danh sách Top N sản phẩm (mặc định N=10, tuỳ chỉnh
  được) theo số lượng bán hoặc theo doanh thu, trong khoảng thời gian chọn.
- Acceptance Criteria:
  - [ ] Tính trên `OrderItem` thuộc các Order có Invoice ở trạng thái `Paid`
        (đồng bộ quy tắc ghi nhận doanh thu với FR-1).
  - [ ] Sắp xếp được theo số lượng bán hoặc theo tổng tiền, giảm dần.
  - [ ] Hiển thị đúng tên/SKU sản phẩm tại thời điểm bán (snapshot), kể cả khi
        Product đó đã bị xoá mềm hoặc đổi tên sau này.
  - [ ] Trường hợp lỗi: không có dữ liệu trong khoảng thời gian → trả danh
        sách rỗng kèm thông báo rõ ràng, không phải lỗi hệ thống.

### FR-3: Báo cáo tồn kho (Inventory Report)
- Mô tả: Quản lý xem tổng quan tồn kho hiện tại — số sản phẩm hết hàng, số
  sản phẩm tồn thấp, giá trị tồn kho ước tính (tổng `quantity × cost_price`
  toàn bộ Product đang active) — và lịch sử nhập/xuất trong khoảng thời gian
  chọn.
- Acceptance Criteria:
  - [ ] Danh sách sản phẩm tồn thấp/hết hàng dùng đúng quy tắc `stock_status`
        đã định nghĩa ở Inventory Management (`0 < quantity <= threshold` =
        tồn thấp, `quantity = 0` = hết hàng).
  - [ ] Tổng nhập, tổng xuất, tổng điều chỉnh trong khoảng thời gian chọn,
        tính từ `StockMovement`.
  - [ ] Giá trị tồn kho ước tính chỉ tính Product còn active (không tính
        Product đã xoá mềm).
  - [ ] Trường hợp lỗi: Product có Inventory nhưng `cost_price` bằng 0 (không
        hợp lệ theo constraint của Product) không thể xảy ra — không cần xử
        lý, nhưng nếu Product chưa có `Inventory` record thì loại khỏi báo
        cáo tồn kho thay vì lỗi.

### FR-4: Báo cáo phương thức thanh toán (Payment Method Breakdown)
- Mô tả: Quản lý xem số lượng và tổng tiền giao dịch theo `payment_method`
  (QR/Manual) và theo `provider` (SePay/Manual), cùng tỉ lệ thành công/thất
  bại, trong khoảng thời gian chọn.
- Acceptance Criteria:
  - [ ] Tính trên `Payment`/`PaymentTransaction` theo `status` (`Success`,
        `Failed`, `Expired`, `Cancelled`, `Pending`, `Processing`).
  - [ ] Chỉ `Success` được cộng vào "tổng tiền thu được"; các trạng thái khác
        chỉ đếm số lượng để đo tỉ lệ thất bại.
  - [ ] Trường hợp lỗi: không có giao dịch nào trong khoảng thời gian → trả
        báo cáo rỗng, không lỗi.

### FR-5: Báo cáo khách hàng (Customer Report)
- Mô tả: Quản lý xem Top khách hàng theo tổng chi tiêu (dựa trên Invoice
  `Paid`) và số lượng khách hàng mới đăng ký trong khoảng thời gian chọn.
- Acceptance Criteria:
  - [ ] Top khách hàng sắp xếp theo tổng `total_amount` các Invoice `Paid`,
        giảm dần, giới hạn Top N tuỳ chỉnh (mặc định 10).
  - [ ] Khách hàng mới đếm theo `Customer.created_at` nằm trong khoảng thời
        gian chọn, không phân biệt trạng thái Customer.
  - [ ] Trường hợp lỗi: khách hàng đã bị xoá mềm vẫn được tính vào Top nếu có
        Invoice `Paid` trong lịch sử (không loại khỏi báo cáo doanh thu quá
        khứ).

### FR-6: Xuất báo cáo ra CSV (Export)
- Mô tả: Với mỗi loại báo cáo ở FR-1 đến FR-5, Quản lý xuất được kết quả đang
  xem ra file CSV, dùng đúng bộ lọc (khoảng thời gian, Top N...) hiện tại.
- Acceptance Criteria:
  - [ ] File CSV có header rõ ràng bằng tiếng Việt, encoding UTF-8 (mở đúng
        dấu trên Excel).
  - [ ] Xuất đúng dữ liệu đang hiển thị trên báo cáo tương ứng, không xuất dữ
        liệu ngoài phạm vi filter đang chọn.
  - [ ] Trường hợp lỗi: không có quyền `export:report` → 403, không cho tải
        file.

## 9. Quy tắc nghiệp vụ & Validation

- **Định nghĩa "doanh thu"**: chỉ tính Invoice ở trạng thái `Paid`. Không
  dùng Order hay Payment làm nguồn doanh thu chính vì: Order có thể ở trạng
  thái `Paid`/`Completed` mà chưa phát sinh Invoice hợp lệ (dữ liệu cũ/luồng
  lỗi), còn một Invoice có thể có nhiều `Payment`/`PaymentTransaction` (thử
  lại sau khi thất bại) nên cộng trực tiếp theo Payment dễ đếm trùng.
- Khoảng thời gian filter (`from`, `to`) áp dụng cho **toàn bộ báo cáo** theo
  cùng field mốc thời gian: `paid_at` cho báo cáo doanh thu/sản phẩm/khách
  hàng, `processed_at` cho báo cáo thanh toán, `created_at` cho báo cáo tồn
  kho (StockMovement).
- `from` phải nhỏ hơn hoặc bằng `to`; nếu không truyền, mặc định 30 ngày gần
  nhất tính đến thời điểm hiện tại (giờ Việt Nam, `Asia/Ho_Chi_Minh`).
- Top N cho FR-2/FR-5 giới hạn tối đa 100 để tránh truy vấn quá nặng.
- Toàn bộ số tiền hiển thị đơn vị `VND`, không quy đổi tiền tệ khác dù field
  `currency` tồn tại trên Order/Invoice/Payment.
- Báo cáo không sửa/ghi bất kỳ dữ liệu nào của module khác — vi phạm nguyên
  tắc "Selector chỉ đọc" nếu có bất kỳ thao tác ghi nào trong luồng xem báo
  cáo.

## 10. Phân quyền (RBAC — theo nghiệp vụ, không phải tên class)

| Action | Actor được phép |
|---|---|
| Xem (View) | Quản lý; Superuser luôn được phép |
| Xuất dữ liệu (Export) | Quản lý; Superuser luôn được phép |

Không có Tạo/Sửa/Xoá vì Report không có entity riêng. Nhân viên bán hàng
không có quyền `view:report`/`export:report` mặc định — resource `report` đã
tồn tại sẵn trong `PermissionResource` (`apps/accounts/constants.py`) từ
Sprint 1 nhưng cần seed hai permission (`view:report`, `export:report`) và
gán vào role Quản lý khi triển khai.

## 11. Yêu cầu phi chức năng (Non-functional, nếu có)

- **Hiệu năng**: mỗi báo cáo phải dùng aggregate query ở tầng DB (`Sum`,
  `Count`, `annotate`...), không được load toàn bộ record về Python rồi cộng
  tay. Mục tiêu dưới 3 giây cho dữ liệu 1 năm ở quy mô một cửa hàng (mục 3).
- **Cache**: kết quả báo cáo là ứng viên cache hợp lệ theo
  `coding-convention.md` §21 ("Report results" được liệt kê là good candidate)
  — có thể cache theo Redis với TTL ngắn (vài phút) khoá theo tham số filter,
  và phải invalidate hoặc chấp nhận độ trễ ngắn khi có Invoice/Payment mới
  phát sinh trong khoảng thời gian đang cache.
- **Bảo mật**: doanh thu, lợi nhuận, chi tiêu khách hàng là dữ liệu nhạy cảm
  — không hiển thị cho role không có `view:report`. Không log số tiền cụ thể
  ra console log ở mức INFO (tuân theo coding-convention §11 chỉ áp dụng cho
  secrets, nhưng dữ liệu doanh thu nội bộ cũng nên tránh log tràn lan).
- **Phân trang**: các báo cáo dạng danh sách (Top sản phẩm, Top khách hàng,
  danh sách tồn thấp...) áp dụng phân trang chuẩn của dự án nếu số dòng vượt
  quá một trang mặc định.

## 12. Câu hỏi mở / Rủi ro (Open Questions / Risks)

- Doanh thu tính theo Invoice `Paid` (quyết định trong mục 9) có đúng với kỳ
  vọng nghiệp vụ thực tế không, hay cần tính theo Order? Cần Product
  Owner/giảng viên hướng dẫn xác nhận trước khi convert sang prompt kỹ thuật.
- Có cần báo cáo doanh thu/số đơn theo từng nhân viên bán hàng
  (`Order.created_by`) ở sprint này không, hay để hẳn sprint sau (hiện đang
  để Non-goal)?
- TTL cache cụ thể là bao nhiêu phút? Cần chốt theo mức độ "gần real-time" mà
  Quản lý mong muốn khi xem báo cáo doanh thu trong ngày.
- Giới hạn xa nhất cho khoảng thời gian filter là bao lâu (1 năm? không giới
  hạn)? Ảnh hưởng trực tiếp tới NFR hiệu năng.
- Export CSV có cần giới hạn số dòng tối đa (vd. 10.000 dòng) để tránh timeout
  không?

## 13. Bước tiếp theo

- [ ] PRD được review & approve bởi: _(chưa điền)_
- [ ] Convert sang prompt kỹ thuật theo [`docs/prompt-features.md`](prompt-features.md)
- [ ] Triển khai theo [README.md § Quy tắc Coding & Triển khai](../README.md#quy-tắc-coding--triển-khai)
- [ ] Ghi lại kết quả tại `docs/sprint_5.md`
