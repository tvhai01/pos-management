# Prompt Rules — Chuẩn hoá yêu cầu triển khai tính năng

## Mục đích

File này là **bộ quy tắc viết prompt/task** dùng khi giao một tính năng hoặc
module nghiệp vụ mới cho AI agent (Claude Code, ChatGPT, ...) hoặc brief cho
một dev khác trong team. Mục tiêu: mọi tính năng — dù ai viết prompt, dù ai
triển khai — đều đi qua cùng một khuôn thông tin, để output luôn:

- **Đúng kiến trúc** đã thiết lập ở [README.md § Quy tắc Coding & Triển khai](../README.md#quy-tắc-coding--triển-khai).
- **Đầy đủ** — không thiếu layer (thiếu test, thiếu migration, thiếu cập nhật README...).
- **Nhất quán** giữa các sprint — Sprint N+1 đọc lại Sprint N mà không bị lệch pattern.

Bốn tài liệu này liên kết chặt với nhau, đọc theo vòng, bắt đầu từ PRD:

```
docs/template-PRD.md  ──(điền PRD, mô tả nghiệp vụ)──▶  PRD đã duyệt
        │                                                     │
        │                                     (convert sang prompt kỹ thuật)
        ▼                                                     ▼
README.md  ──(quy tắc code)──▶  prompt-features.md  ──(khi tạo prompt, tham chiếu ngược)──▶  README.md
    ▲                                     │
    │                                     ▼
docs/sprint_N.md  ◀── (mỗi tính năng triển khai xong phải ghi lại kết quả, đối chiếu ngược cả PRD) ──┘
```

- [`docs/template-PRD.md`](template-PRD.md) quy định **yêu cầu sản phẩm phải
  viết như thế nào** — bài toán nghiệp vụ, actor, entity, chức năng ở mức yêu
  cầu, chưa đụng tới kiến trúc code. Là bước bắt buộc **trước** file này.
- `README.md` quy định **code phải trông như thế nào** (layer, RBAC, soft
  delete, response envelope, testing...).
- `prompt-features.md` (file này) quy định **prompt/task yêu cầu tính năng
  phải viết như thế nào** để AI/dev có đủ thông tin áp dụng đúng README, dựa
  trên PRD đã duyệt ở bước trước.
- `docs/sprint_N.md` là **bằng chứng đã làm đúng** — tài liệu hoá lại những gì
  đã triển khai, đối chiếu được với PRD gốc, prompt gốc, và với README.

> Nếu một trong bốn tài liệu thay đổi (vd. thêm quy tắc mới vào README), phải
> rà soát lại các tài liệu còn lại xem có cần cập nhật mục tương ứng không —
> tránh để chúng lệch nhau.

## Khi nào dùng file này

Dùng template ở dưới **mỗi khi**, và **sau khi** đã có PRD được duyệt theo
[`docs/template-PRD.md`](template-PRD.md):

- Thêm một module nghiệp vụ mới (Product, Inventory, Order, Invoice, Payment, ...).
- Thêm một entity mới vào module đã có (vd. thêm "Customer Group" vào Customer Management).
- Yêu cầu AI agent tự triển khai một tính năng full-stack (model → API → test).

Không cần dùng cho: sửa bug nhỏ, refactor không đổi hành vi, thay đổi cấu hình
hạ tầng (Docker, CI...) — những việc đó mô tả trực tiếp, không cần theo khuôn
này (và cũng không cần PRD).

> Nếu chưa có PRD (task nhỏ, không đáng viết PRD đầy đủ), điền thẳng template
> bên dưới nhưng phải tự trả lời được các câu hỏi "làm gì / cho ai / vì sao"
> trong đầu trước — đừng bỏ qua bước tư duy đó chỉ vì bỏ qua tài liệu.

## Nguyên tắc bắt buộc khi viết prompt

1. **Không được mơ hồ ở entity & field.** Liệt kê rõ từng field, kiểu dữ liệu
   ngầm định (unique? optional? enum?). AI/dev không được tự đoán field.
2. **Enum trạng thái phải khai báo tường minh** (dùng `TextChoices`, xem
   README mục 6) — không để trạng thái là chuỗi tự do.
3. **RBAC phải liệt kê đủ action** cho resource (`view/create/update/delete`,
   thêm `export`/`import`/`approve` nếu nghiệp vụ cần) — không được thiếu rồi
   bổ sung sau, vì thêm permission sau sẽ cần migration mới.
4. **API phải khớp REST convention đã dùng** trong dự án: `POST` (create),
   `GET` list + `GET {id}` (read), `PUT`/`PATCH` (update — xem README mục 6
   để biết khi nào field bắt buộc, khi nào optional), `DELETE` (xoá — mặc định
   là **soft delete** theo README mục 5, trừ khi prompt nói rõ là hard delete
   và giải thích lý do).
5. **Validation phải nêu rõ** field nào cần unique, field nào cần đúng định
   dạng (email, phone, ...) — đây là input cho `serializers.py`, không phải
   thứ để AI tự bịa thêm.
6. **Kiến trúc phải nhắc lại rõ ràng** thứ tự layer bắt buộc (View → Serializer
   → Service → Selector → ORM) — kể cả khi đã có trong README, nhắc lại trong
   prompt giúp AI không "tiện tay" viết tắt (gọi ORM thẳng từ view, nhét
   business logic vào serializer...).
7. **Test phải liệt kê theo hành vi**, không chỉ nói chung chung "viết test".
   Ít nhất phải có: tạo, sửa, xoá, tìm kiếm/lọc, và permission check (có
   quyền / không có quyền / superuser bypass).
8. **Output phải là một checklist**, không phải một đoạn văn — để AI/dev tick
   được từng mục và người review biết ngay thiếu gì.
9. **Không được yêu cầu sửa `apps/accounts`** ngoại trừ thêm entry vào
   `PermissionResource` (xem README mục 4) — nếu task cần sửa gì khác trong
   `apps/accounts`, phải nêu lý do tường minh trong prompt, không để AI tự
   quyết định.

## Template chuẩn (copy để điền)

```text
Implement Sprint <N>: <Tên module> Module

CONTEXT
- Các module đã có: <liệt kê, vd. Authentication, JWT, RBAC, User, Role, Customer>.
- Không sửa <module không được đụng vào> trừ khi thực sự bắt buộc.
- Tuân theo kiến trúc & coding rules hiện có của dự án (README.md).

TECHNOLOGY
- Django 6.0 / DRF / PostgreSQL / JWT / RBAC (giữ nguyên, không đổi stack trừ khi nêu rõ).

GOAL
- Mô tả 1-2 câu: module này giải quyết bài toán nghiệp vụ gì, là nền tảng cho
  module nào sau này (nếu có).

<TÊN_ENTITY> ENTITY
- Liệt kê đầy đủ field, ghi chú field nào unique/optional/enum.
  id
  <field_1> (unique nếu có)
  <field_2>
  ...
  status
  created_at / updated_at / created_by / updated_by   (mặc định có sẵn qua AuditModel)

STATUS
- Dùng TextChoices, liệt kê đủ giá trị:
  VALUE_1
  VALUE_2
  ...

FEATURES
1. Create <Entity>
2. Update <Entity>
3. Delete <Entity> (Soft Delete — trừ khi nêu rõ lý do cần hard delete)
4. <Entity> Detail
5. <Entity> List
6. Search <Entity>
   Search By: <liệt kê field tìm kiếm được>
7. Pagination
8. Sorting
9. Filter By <field, thường là status>

RBAC
<Entity>.View
<Entity>.Create
<Entity>.Update
<Entity>.Delete
<Entity>.Export        (nếu nghiệp vụ cần xuất dữ liệu — có thể khai báo permission trước, chưa cần endpoint)

API
POST   /api/v1/<entities>
GET    /api/v1/<entities>
GET    /api/v1/<entities>/{id}
PUT    /api/v1/<entities>/{id}
DELETE /api/v1/<entities>/{id}

VALIDATION
- <field> format validation (nếu có, vd. phone, email)
- Unique <field_1>
- Unique <field_2>

ARCHITECTURE
Views → Serializer → Service → Selector → ORM → PostgreSQL
Business Logic phải nằm trong Service Layer. Không query ORM trực tiếp từ View.

TEST
Tạo Unit Test cho:
- Create <Entity>
- Update <Entity>
- Delete <Entity>
- Search <Entity>
- Permission Check (có quyền / không có quyền / superuser bypass)

OUTPUT
1. Folder Structure
2. Models
3. Migration
4. Serializer
5. Service
6. Selector
7. Permission
8. Views
9. URLs
10. Unit Test
11. Cập nhật README (bảng API + FEATURE_MODULES trong config/views.py nếu cần)
12. docs/sprint_<N>.md (Summary → What Was Built → Design Decisions → Files Changed → Next Sprint)
13. Review (chạy pytest --cov, black, ruff check; xác nhận coverage ≥ 80%)
```

## Ví dụ tham chiếu chuẩn (worked example)

Sprint 2 — **Customer Management** — là ví dụ mẫu đã áp dụng đúng toàn bộ
template và quy tắc ở trên. Khi không chắc một mục trong template nghĩa là gì,
đối chiếu trực tiếp với:

- Prompt gốc → cách nó được diễn giải thành code: `apps/customers/`.
- Kết quả cuối cùng, đã tài liệu hoá đầy đủ theo đúng OUTPUT checklist:
  [`docs/sprint_2.md`](sprint_2.md).

Cụ thể một vài đối chiếu đáng chú ý (giải thích *tại sao* để không lặp lại
máy móc mà không hiểu lý do):

| Mục trong prompt | Áp dụng vào code | Vì sao |
|---|---|---|
| `Delete Customer (Soft Delete)` | `is_deleted` + `deleted_at`, `CustomerManager` tự lọc | README mục 5 — resource bị module khác tham chiếu (Order, Invoice) không được xoá cứng |
| `Unique customer_code` / `Unique phone` | `validate_customer_code`/`validate_phone` trong serializer, dùng `CustomerSelector.code_exists`/`phone_exists` | README mục 6 — validate ở serializer, DB constraint chỉ là lớp chặn cuối |
| `RBAC: Customer.View/.Create/.Update/.Delete/.Export` | `PermissionResource.CUSTOMER` (đã có sẵn trong `apps/accounts/constants.py`) + `apps/customers/permissions.py` khai báo dict hằng số | README mục 4 — không viết permission class riêng, tái sử dụng `HasPermission` |
| `Pagination/Sorting/Filter` | `CustomerListCreateView(GenericAPIView)` + `shared.pagination.paginated_success_response` | README mục 7 — không tự viết lại logic phân trang |
| `TEST: Permission Check` | `test_create_customer_without_permission`, `test_superuser_can_create_customer`, ... | README mục 8 — bắt buộc test cả 3 trường hợp permission |

## Sau khi AI/dev triển khai xong — checklist review

Người review (hoặc chính AI agent, ở bước cuối) phải xác nhận:

- [ ] Cấu trúc file đúng mục 2 trong README (không thiếu, không thừa file lạ).
- [ ] Không có ORM call trong `views.py`.
- [ ] Không có business logic trong `serializers.py` (chỉ validate/format).
- [ ] RBAC dùng `HasPermission` có sẵn, không tự viết permission class mới.
- [ ] Soft delete đúng pattern (nếu resource cần).
- [ ] `docker compose exec backend pytest --cov` pass, coverage ≥ 80%.
- [ ] `black .` và `ruff check .` không phát sinh lỗi **mới** (nợ kỹ thuật cũ
      như `RUF012` đã biết, xem README mục 9, không phải lý do chặn PR).
- [ ] README đã cập nhật bảng API tương ứng.
- [ ] `docs/sprint_N.md` đã được tạo, theo đúng cấu trúc chuẩn.
- [ ] Không có thay đổi ngoài phạm vi ở `apps/accounts` (trừ `PermissionResource`).
- [ ] Nếu có PRD gốc (`docs/template-PRD.md`), đối chiếu lại: mọi Acceptance
      Criteria trong PRD đều có chức năng/test tương ứng; mọi sai lệch phạm vi
      so với PRD được nêu rõ trong `docs/sprint_N.md`.

Nếu thiếu bất kỳ mục nào ở trên, tính năng **chưa được coi là hoàn thành**,
kể cả khi API "chạy được".
