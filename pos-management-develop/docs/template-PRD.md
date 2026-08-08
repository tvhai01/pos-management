# Template PRD — Product Requirements Document cho Module mới

## Mục đích

File này là **template chuẩn** để mô tả yêu cầu sản phẩm (business requirements)
cho một module/tính năng mới, **trước khi** viết prompt kỹ thuật giao cho AI
agent hoặc dev. PRD trả lời **"làm cái gì, cho ai, vì sao"** — khác với
[`docs/prompt-features.md`](prompt-features.md) trả lời **"triển khai như thế
nào cho đúng kiến trúc dự án"**.

Ba tài liệu liên kết với nhau theo đúng một vòng, PRD là bước khởi đầu:

```
docs/template-PRD.md   ──(điền PRD, mô tả nghiệp vụ)──▶   PRD đã duyệt
        │                                                        │
        │                                          (convert sang prompt kỹ thuật,
        │                                           theo khuôn prompt-features.md)
        ▼                                                        ▼
README.md § Quy tắc Coding  ◀──(code phải tuân theo)──   docs/prompt-features.md
        │
        ▼
docs/sprint_N.md  ◀── (triển khai xong, ghi lại kết quả, đối chiếu ngược với PRD) 
```

- **PRD (file này)** — Product Owner / dev viết, mô tả bài toán nghiệp vụ,
  actor, phạm vi, entity, chức năng ở mức yêu cầu. **Không** chứa chi tiết kiến
  trúc code (layer, tên class...).
- **`prompt-features.md`** — convert PRD đã duyệt thành prompt kỹ thuật theo
  khuôn có sẵn, tham chiếu đúng [README.md § Quy tắc Coding & Triển
  khai](../README.md#quy-tắc-coding--triển-khai).
- **`docs/sprint_N.md`** — ghi lại kết quả triển khai thực tế, đối chiếu ngược
  với PRD để review có đi đúng yêu cầu ban đầu không.

## Khi nào dùng file này

- Trước khi thêm một **module nghiệp vụ mới** (Product, Inventory, Order,
  Invoice, Payment, ...).
- Trước khi thêm một **entity mới đáng kể** vào module đã có (vd. "Customer
  Group" vào Customer Management) — nếu chỉ thêm 1 field nhỏ, không cần PRD
  đầy đủ, mô tả trực tiếp trong prompt kỹ thuật là đủ.

Không cần dùng cho: sửa bug, refactor không đổi hành vi, thay đổi cấu hình hạ
tầng — những việc đó không có "yêu cầu sản phẩm" mới để mô tả.

## Nguyên tắc khi điền PRD

1. **Viết cho người đọc không phải dev** — actor, goal, use case phải hiểu
   được mà không cần biết Django/DRF là gì. Chi tiết kỹ thuật (tên field kiểu
   gì trong ORM, layer nào gọi layer nào...) thuộc về prompt kỹ thuật, không
   thuộc về PRD.
2. **Mỗi chức năng phải có Acceptance Criteria** — điều kiện để coi là "xong",
   không phải mô tả chung chung.
3. **Phạm vi phải tách rõ In Scope / Out of Scope** — tránh scope creep khi
   convert sang prompt kỹ thuật.
4. **Entity & trạng thái phải liệt kê đủ**, dù ở mức nghiệp vụ (không cần kiểu
   dữ liệu ORM) — đây là input bắt buộc để điền mục `ENTITY`/`STATUS` của
   `prompt-features.md` sau này.
5. **RBAC phải nêu actor nào làm được gì** — không cần biết tên permission
   class, chỉ cần biết "role nào được create/view/update/delete/export".
6. **Không tự quyết kiến trúc thay dev/AI** — PRD không được chỉ định layer,
   tên file, tên class. Đó là việc của bước prompt kỹ thuật.
7. **Nêu rõ phụ thuộc vào module khác** — vd. "Order tham chiếu Customer" —
   để bước kỹ thuật biết soft delete/FK nào cần giữ nguyên.

## Template chuẩn (copy để điền)

```text
# PRD: <Tên module>

## 1. Thông tin chung
- Module: <tên module>
- Sprint dự kiến: <N>
- Người viết PRD: <tên>
- Ngày: <YYYY-MM-DD>
- Trạng thái: Draft / Reviewing / Approved

## 2. Bối cảnh & Vấn đề (Problem Statement)
- Vấn đề nghiệp vụ hiện tại là gì? Ai đang gặp vấn đề này?
- Vì sao cần giải quyết bây giờ (ưu tiên, phụ thuộc module khác...)?

## 3. Mục tiêu (Goals)
- Mục tiêu 1: <mô tả, đo lường được nếu có thể>
- Mục tiêu 2: ...

## 4. Ngoài phạm vi (Non-goals / Out of Scope)
- <Điều gì KHÔNG làm ở module/sprint này, dù nghe liên quan>
- <Để dành cho sprint sau, ghi rõ lý do>

## 5. Đối tượng sử dụng (Actors / User Roles)
| Actor | Vai trò trong module này |
|---|---|
| <vd. Nhân viên bán hàng> | <vd. Tạo và tra cứu đơn hàng của mình> |
| <vd. Quản lý> | <vd. Toàn quyền + duyệt/huỷ đơn> |

## 6. Entity nghiệp vụ
### <Tên Entity>
| Field | Bắt buộc? | Unique? | Ghi chú |
|---|---|---|---|
| <field_1> | Có/Không | Có/Không | <mô tả ý nghĩa nghiệp vụ, định dạng nếu có (email, phone...)> |
| <field_2> | ... | ... | ... |
| status | Có | Không | Xem mục Trạng thái bên dưới |

### Trạng thái (Status)
| Giá trị | Ý nghĩa | Chuyển từ trạng thái nào |
|---|---|---|
| <VALUE_1> | ... | (trạng thái khởi tạo) |
| <VALUE_2> | ... | <VALUE_1> |

## 7. Quan hệ với module khác (Dependencies)
- <Entity này> tham chiếu tới <module khác> qua <field/quan hệ gì>.
- <Module khác> có bị ảnh hưởng khi <entity này> bị xoá/đổi trạng thái không?
- Cần Soft Delete không? (Có nếu entity bị module khác tham chiếu — mặc định
  Có trừ khi giải thích rõ lý do dùng Hard Delete.)

## 8. Chức năng (Functional Requirements)
### FR-1: <Tên chức năng, vd. Tạo đơn hàng>
- Mô tả: <actor nào, làm gì, khi nào>
- Acceptance Criteria:
  - [ ] <điều kiện 1>
  - [ ] <điều kiện 2>
  - [ ] Trường hợp lỗi: <điều gì xảy ra khi input sai/thiếu quyền/trùng dữ liệu>

### FR-2: <Tên chức năng>
- Mô tả: ...
- Acceptance Criteria:
  - [ ] ...

(Lặp lại cho từng chức năng: Create / Update / Delete / Detail / List / Search
/ Filter / Sort / Pagination / các action nghiệp vụ riêng như Export, Approve...)

## 9. Quy tắc nghiệp vụ & Validation
- <Quy tắc 1, vd. "Không được tạo đơn hàng nếu khách hàng đang ở trạng thái Blocked">
- <Field nào cần unique>
- <Field nào cần đúng định dạng — email, phone, mã...>
- <Ràng buộc số lượng/giá trị, nếu có>

## 10. Phân quyền (RBAC — theo nghiệp vụ, không phải tên class)
| Action | Actor được phép |
|---|---|
| Xem (View) | <role> |
| Tạo (Create) | <role> |
| Sửa (Update) | <role> |
| Xoá (Delete) | <role> |
| Xuất dữ liệu (Export) | <role, nếu có> |
| <action nghiệp vụ khác> | <role> |

## 11. Yêu cầu phi chức năng (Non-functional, nếu có)
- Hiệu năng: <vd. danh sách phải hỗ trợ phân trang, tối đa bao nhiêu bản ghi/trang>
- Bảo mật: <vd. dữ liệu nhạy cảm nào cần ẩn khỏi role thường>
- Khác: <nếu có>

## 12. Câu hỏi mở / Rủi ro (Open Questions / Risks)
- <Điều gì chưa rõ, cần chốt trước khi convert sang prompt kỹ thuật>

## 13. Bước tiếp theo
- [ ] PRD được review & approve bởi: <tên>
- [ ] Convert sang prompt kỹ thuật theo [`docs/prompt-features.md`](prompt-features.md)
- [ ] Triển khai theo [README.md § Quy tắc Coding & Triển khai](../README.md#quy-tắc-coding--triển-khai)
- [ ] Ghi lại kết quả tại `docs/sprint_<N>.md`
```

## Ví dụ tham chiếu

Chưa có PRD nào được viết lại hồi tố cho Sprint 1/2 (được triển khai trước khi
template này tồn tại). Khi PRD đầu tiên theo template này được duyệt và triển
khai, thêm một dòng đối chiếu vào đây (PRD → prompt → `sprint_N.md`) để làm ví
dụ mẫu cho các module sau, theo đúng tinh thần "worked example" đã áp dụng ở
[`docs/prompt-features.md`](prompt-features.md) với Sprint 2 — Customer
Management.

## Tài liệu liên quan

| Tài liệu | Mục đích |
|---|---|
| [`README.md`](../README.md#quy-tắc-coding--triển-khai) | Quy tắc code phải tuân theo (kiến trúc, RBAC, soft delete, testing...). |
| [`docs/prompt-features.md`](prompt-features.md) | Template prompt kỹ thuật — bước sau khi PRD được duyệt. |
| [`docs/sprint_2.md`](sprint_2.md) | Ví dụ module đã triển khai hoàn chỉnh, đối chiếu được với PRD/prompt. |
