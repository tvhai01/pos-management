# Sprint 7 — Report: Chart + AI Insight

**Trạng thái:** Hoàn thành (cần verify lại bằng `docker compose exec backend pytest --cov` — xem mục Kiểm thử)
**Ngày hoàn thành:** 2026-09-14

## Mục tiêu

Sau Sprint 5 (`docs/sprint_5.md`, PRD `docs/prd_report.md`), 5 báo cáo
(Doanh thu, Sản phẩm bán chạy, Tồn kho, Thanh toán, Khách hàng) chỉ hiển thị
bảng số liệu thuần — quản lý phải tự đọc số để ra quyết định. Sprint này bổ
sung (1) biểu đồ trực quan cho cả 5 báo cáo, và (2) một lớp "AI Insight"
sinh nhận xét + đề xuất bằng tiếng Việt dựa trên số liệu đang xem, theo yêu
cầu người dùng. Không phải report builder tuỳ biến — vẫn nằm trong Non-goal
của PRD gốc, chỉ là lớp diễn giải thêm cho 5 báo cáo cố định đã có (xem
`docs/prd_report.md` §14 Addendum).

## Công việc đã hoàn thành

### AI Insight — `apps/reports/`
- `apps/reports/ai/providers.py`: `GeminiProvider`, `GroqProvider` — gọi
  HTTP bằng `urllib` thuần (theo đúng pattern `apps/payments/sepay.py`,
  không thêm dependency `requests`/`httpx`). Thiếu API key → raise
  `AIProviderError` ngay, không gọi mạng.
- `apps/reports/ai/prompts.py`: `build_prompt` — build prompt tiếng Việt
  yêu cầu AI trả JSON `{"summary", "recommendations"}`. Với báo cáo khách
  hàng, loại bỏ `customer__full_name` khỏi payload trước khi gửi ra ngoài
  — chỉ gửi `customer_code` + số liệu.
- `apps/reports/insights.py`: `RuleBasedInsightGenerator` — engine thống
  kê/ngưỡng tự viết, không gọi mạng, không bao giờ raise. Là fallback cuối
  cùng và chạy mặc định khi chưa cấu hình API key nào (đúng trạng thái môi
  trường dev hiện tại).
- `apps/reports/services.py`: `ReportInsightService` — Service đầu tiên
  của app `reports` (trước đây không có Service vì Report chỉ đọc, không
  ghi — xem docstring cũ của `views.py`). Orchestrate chuỗi fallback
  **Gemini → Groq → rule-based**, cache kết quả theo Redis
  (`AI_INSIGHT_CACHE_TTL`, mặc định 900s) khoá theo loại báo cáo + tham số
  filter.
- `apps/reports/constants.py`: thêm `ReportType`, `AIInsightSource`
  (`TextChoices`).
- Settings mới (`config/settings/base.py`, `.env.example`): `GEMINI_API_KEY`,
  `GEMINI_API_URL`, `GEMINI_MODEL`, `GROQ_API_KEY`, `GROQ_API_URL`,
  `GROQ_MODEL`, `AI_INSIGHT_TIMEOUT`, `AI_INSIGHT_CACHE_TTL` — tất cả có
  default hợp lý, để trống vẫn chạy được (rơi về rule-based).

### API — `apps/reports/views.py` + `urls.py`
5 endpoint mới, permission `view:report` (không phải `export:report` — xem
insight không phải xuất dữ liệu thô):
`GET /api/v1/reports/revenue/insights/`,
`.../products/top-selling/insights/`, `.../inventory/insights/`,
`.../payments/breakdown/insights/`, `.../customers/insights/`.

### Dashboard — `apps/dashboard/`
- 5 view JSON mới (`report_*_insights`), theo đúng pattern hiện có (dashboard
  gọi thẳng `ReportSelector`, không qua REST API riêng của nó) — mirror cấu
  trúc `report_*_export` nhưng trả `JsonResponse` thay vì CSV.
- Template `dashboard/reports/index.html`: nạp Chart.js qua CDN, mỗi báo cáo
  có 1 canvas (line cho doanh thu theo kỳ, bar cho top sản phẩm và top khách
  hàng, bar cho nhập/xuất/điều chỉnh tồn kho, doughnut cho tỉ trọng phương
  thức thanh toán) + nút "🔎 Phân tích AI" gọi `fetch()` tới endpoint JSON
  tương ứng, hiện `summary`/`recommendations`/nguồn (Gemini/Groq/Rule-based).

## Quyết định thiết kế

- **Fallback 3 lớp thay vì chỉ 1 provider**: free tier của Gemini/Groq có
  rate limit, và đồ án cần chạy demo ổn định không phụ thuộc mạng/quota —
  rule-based đảm bảo tính năng luôn trả kết quả hợp lý.
- **Kích hoạt bằng nút bấm, không tự động**: tránh gọi AI mỗi lần đổi
  filter, giữ quota free tier cho lúc cần demo thật.
- **Không gửi tên khách hàng ra ngoài**: dữ liệu doanh thu/khách hàng là
  nội bộ nhạy cảm (PRD gốc §11) — payload gửi Gemini/Groq cho báo cáo khách
  hàng chỉ có `customer_code` + số liệu, không có `full_name`.
- **Cache theo Redis, không cache trong-process**: dự án đã dùng
  `django-redis` sẵn cho mọi cache khác (coding-convention §21), tái dùng
  hạ tầng có sẵn thay vì thêm cơ chế cache riêng.
- **`ReportInsightService` là Service đầu tiên của app `reports`**: gọi
  provider ngoài + fallback + cache là business logic thật (coding-
  convention §3.1), không phù hợp đặt trong View hay Selector (Selector chỉ
  đọc DB, không có I/O ngoài).

## Kiểm thử

- `apps/reports/tests/test_insights.py` (mới, 15 test): `RuleBasedInsight
  Generator` cho cả 5 loại báo cáo (case rỗng/khoẻ mạnh và case có vấn đề:
  doanh thu giảm, tồn kho hết hàng, thanh toán thất bại cao, khách hàng phụ
  thuộc 1 khách); `ReportInsightService` mock `GeminiProvider`/`GroqProvider`
  để test đủ nhánh fallback (Gemini thành công / Gemini lỗi → Groq / cả hai
  lỗi → rule-based / output không parse được → rule-based) + test cache
  (gọi 2 lần cùng tham số chỉ gọi provider 1 lần).
- `apps/reports/tests/test_views.py`: bổ sung 5 test class cho 5 endpoint
  insight mới (401 chưa đăng nhập, 403 thiếu quyền, 200 + đúng field khi có
  quyền, superuser bypass) — chạy với `GEMINI_API_KEY`/`GROQ_API_KEY` rỗng
  (`@override_settings`) nên xác nhận nhánh rule-based qua đúng luồng
  View → Selector → Service, không gọi mạng thật.
- **Đã verify trong môi trường này** (không có Docker/Postgres/Redis khả
  dụng): `python -m py_compile` toàn bộ file mới/sửa, `black --check` và
  `ruff check` sạch (không phát sinh lỗi mới), và chạy trực tiếp bằng
  `pytest` (venv tạm + SQLite/LocMemCache, không cần DB) cho
  `test_insights.py` — **15/15 passed**.
- **Chưa verify được trong môi trường này** (cần Postgres/Redis thật, tức
  `docker compose exec backend pytest --cov`): 5 test class DB-dependent
  trong `test_views.py`, coverage tổng thể ≥ 80%, và đường gọi Gemini/Groq
  thật (chưa có API key thật để test end-to-end — nhánh fallback rule-based
  được test bằng mock, xem trên). Cần chạy `docker compose exec backend
  pytest --cov` trên máy có Docker trước khi coi sprint này là "đã kiểm thử
  đầy đủ" theo checklist `docs/prompt-features.md`.
- Chưa verify UI qua trình duyệt thật (không có Docker để chạy `docker
  compose up`) — cần tự kiểm tra: vào `/reports/`, xác nhận chart hiển thị
  đúng số liệu, bấm "Phân tích AI" mỗi card ra kết quả (nguồn sẽ là
  Rule-based nếu chưa điền `GEMINI_API_KEY`/`GROQ_API_KEY` vào `.env`).

## Hướng tích hợp sprint sau

- Nếu muốn test đường gọi Gemini/Groq thật: điền `GEMINI_API_KEY` và/hoặc
  `GROQ_API_KEY` vào `.env`, verify lại nhãn nguồn hiển thị đúng "Gemini"/
  "Groq" thay vì "Rule-based".
- Cân nhắc thêm biểu đồ so sánh kỳ này với kỳ trước nếu PRD gốc mở lại Non-
  goal "so sánh kỳ" (`docs/prd_report.md` §4).
- Theo dõi chi phí/quota thật khi lên production — nếu vượt free tier,
  `AI_INSIGHT_CACHE_TTL` có thể tăng lên để giảm tần suất gọi provider.
