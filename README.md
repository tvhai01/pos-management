# POS Management System

Hệ thống Quản lý Bán hàng (Point of Sale) chất lượng production — Đồ án tốt nghiệp UIT.

> 📌 Tài liệu này là **nguồn quy tắc chuẩn (single source of truth)** cho toàn bộ team (kể cả AI agent) khi phát triển thêm tính năng. Trước khi thêm module mới: viết yêu cầu sản phẩm theo [`docs/template-PRD.md`](docs/template-PRD.md), đọc kỹ mục [Quy tắc Coding & Triển khai](#quy-tắc-coding--triển-khai), rồi làm theo quy trình mô tả trong [`docs/prompt-features.md`](docs/prompt-features.md).

## Tech Stack

| Thành phần | Công nghệ |
|---|---|
| **Ngôn ngữ** | Python 3.13 |
| **Framework** | Django 6.0 |
| **API** | Django REST Framework |
| **Database** | PostgreSQL 16 |
| **Cache** | Redis 7 |
| **Auth** | SimpleJWT |
| **Server** | Gunicorn + Nginx |
| **Container** | Docker + Docker Compose |

## Bắt đầu nhanh (Quick Start)

### Yêu cầu

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2+)

### 1. Clone & Cấu hình

```bash
git clone <repository-url>
cd post-project

# Tạo file môi trường từ template
cp .env.example .env
# Chỉnh sửa .env theo nhu cầu (giá trị mặc định đã chạy được ở môi trường dev)
```

### 2. Chạy (Development)

```bash
docker compose up --build
```

API sẽ chạy tại: `http://localhost:8000`

### 3. Kiểm tra

Mỗi lần `docker compose up --build` (hoặc chỉ khởi động lại container
`backend`), entrypoint tự động chạy `python manage.py seed_demo_data` —
lệnh này **idempotent** (chạy lại bao nhiêu lần cũng không tạo trùng dữ
liệu) và **chỉ chạy khi `DEBUG=True`** (không bao giờ đụng vào production).
Sau khi container `backend` lên, database dev sẽ luôn có sẵn:

- 1 tài khoản **Superuser** (dev) — dùng để đăng nhập `/login/` hoặc
  `/admin/`, bypass toàn bộ RBAC.
- Bộ permission đầy đủ (action × resource) + 4 role mẫu theo vị trí thực tế:
  *Quản lý cửa hàng*, *Thu ngân*, *Nhân viên kho*, *Nhân viên bán hàng*.
- **~15 tài khoản nhân viên** demo (`nhanvien01@pos.com` → `nhanvien15@pos.com`),
  phân bổ theo 4 vị trí trên.
- **~100 khách hàng** demo (`CUS0001` → `CUS0100`).

| Loại tài khoản | Email | Mật khẩu | Ghi chú |
|---|---|---|---|
| Superuser | `admin@pos.com` | `PosDev@2026!` | Bypass toàn bộ RBAC |
| Nhân viên demo | `nhanvien01@pos.com` … `nhanvien15@pos.com` | `12345678@` | Phân theo vai trò/vị trí — dùng để test RBAC theo từng quyền hạn khác nhau |

> ⚠️ **Chỉ dùng cho môi trường dev/local.** Không dùng lại các mật khẩu này
> cho production hay bất kỳ môi trường public nào. Trước khi deploy
> production, đổi mật khẩu superuser bằng:
> ```bash
> docker compose exec backend python manage.py changepassword admin@pos.com
> ```
> Muốn tạo thêm superuser cho riêng mình thay vì dùng chung tài khoản trên:
> ```bash
> docker compose exec backend python manage.py createsuperuser
> ```
> Muốn seed lại thủ công (ví dụ sau khi xoá data test) mà không restart
> container:
> ```bash
> docker compose exec backend python manage.py seed_demo_data
> ```

Mở trình duyệt tại `http://localhost:8000/` — đây là **trang quản trị (dashboard UI)**:
chưa đăng nhập sẽ tự chuyển đến `/login/`; đăng nhập bằng tài khoản ở trên (hoặc
tài khoản riêng bạn tự tạo) để vào trang chủ và thao tác như một user bình
thường (theo đúng quyền hạn — RBAC — được gán).

Nếu cần kiểm tra API bằng `curl`/Postman, dùng danh mục module dạng JSON tại
`/api/v1/`:

```bash
curl http://localhost:8000/api/v1/
```

```json
{
  "success": true,
  "message": "Chào mừng đến với POS Management System API.",
  "data": {
    "service": "POS Management System",
    "version": "0.1.0",
    "modules": {
      "health": { "name": "Health Check", "base_url": "/api/v1/health/", "description": "..." },
      "auth": { "name": "Authentication", "base_url": "/api/v1/auth/", "description": "..." },
      "rbac": { "name": "RBAC — Roles & Permissions", "base_url": "/api/v1/roles/", "description": "..." },
      "customers": { "name": "Customer Management", "base_url": "/api/v1/customers/", "description": "..." },
      "admin": { "name": "Django Admin", "base_url": "/admin/", "description": "..." }
    }
  }
}
```

Kiểm tra riêng health check (DB + Redis):

```bash
curl http://localhost:8000/api/v1/health/
```

```json
{
  "success": true,
  "message": "Service is healthy.",
  "data": {
    "status": "ok",
    "version": "0.1.0",
    "database": "connected",
    "redis": "connected"
  }
}
```

### 4. Chạy (Production)

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

## Cấu trúc thư mục

```
post-project/
├── config/          # Cấu hình Django + danh mục module dạng JSON (/api/v1/)
├── apps/            # Các Django app theo từng nghiệp vụ (accounts, customers, dashboard, ...)
├── shared/          # Thành phần dùng chung (base model, response/pagination helper)
├── tests/           # Fixture pytest dùng chung (conftest.py)
├── conftest.py      # File gốc — re-export tests/conftest.py để apps/*/tests dùng được
├── docker/          # Cấu hình Nginx & Gunicorn
├── scripts/         # Script entrypoint & tiện ích
├── requirements/    # Danh sách dependency tách riêng (base/dev/prod)
└── docs/            # Tài liệu theo từng sprint + quy tắc viết prompt tính năng
```

Xem mục [Quy tắc Coding & Triển khai](#quy-tắc-coding--triển-khai) để biết cấu trúc
file bắt buộc bên trong mỗi `apps/<tên-app>/` (`models.py`, `selectors.py`,
`services.py`, ...).

## Kiến trúc (Architecture)

```
HTTP Request → URL → View (thin) → Serializer → Service → Selector → ORM → PostgreSQL
```

| Layer | Trách nhiệm |
|---|---|
| Views | Chỉ xử lý giao diện HTTP |
| Serializers | Validate & định dạng dữ liệu |
| Services | Business logic |
| Selectors | Truy vấn dữ liệu (read-only) |
| Models | Biểu diễn dữ liệu |

Đây là bảng tóm tắt — bản đầy đủ, có thể áp dụng trực tiếp khi code nằm ở mục
[Quy tắc Coding & Triển khai](#quy-tắc-coding--triển-khai) bên dưới. Bắt buộc đọc
trước khi thêm module mới, áp dụng cho cả dev lẫn AI agent.

> **Hai transport, cùng một lớp Service/Selector.** `apps/accounts`,
> `apps/customers` phục vụ JSON qua DRF (`Serializer` + `HasPermission`).
> `apps/dashboard` phục vụ HTML qua session (`Form` thay cho `Serializer`,
> `require_permission` thay cho `HasPermission`) — nhưng cả hai đều gọi
> **chung một** `Service`/`Selector` bên dưới, không có business logic nào bị
> viết lặp lại giữa hai transport. Xem mục 11 trong Quy tắc Coding.

## Tài liệu API

### Trang quản trị (Dashboard UI)

Giao diện HTML, đăng nhập bằng **session** (khác với JWT dùng cho các endpoint
`/api/v1/...` bên dưới). Người dùng thường (không cần `is_staff`) đăng nhập và
thao tác theo đúng quyền (RBAC) được gán cho tài khoản của mình. Module không
đủ quyền xem sẽ không hiển thị trên trang chủ; cố tình vào thẳng URL sẽ nhận
trang 403.

| Method | Endpoint | Mô tả | Auth | Permission |
|---|---|---|---|---|
| `GET` | `/` | Trang chủ — danh mục chức năng theo quyền của user | Session | Đăng nhập |
| `GET`/`POST` | `/login/` | Đăng nhập | Không | — |
| `POST` | `/logout/` | Đăng xuất | Session | Đăng nhập |
| `GET` | `/customers/` | Danh sách/tìm kiếm/lọc khách hàng (có phân trang) | Session | `view:customer` |
| `GET`/`POST` | `/customers/create/` | Form tạo khách hàng | Session | `create:customer` |
| `GET`/`POST` | `/customers/{id}/edit/` | Form sửa khách hàng | Session | `update:customer` |
| `GET`/`POST` | `/customers/{id}/delete/` | Xác nhận rồi xoá mềm khách hàng | Session | `delete:customer` |
| `GET` | `/staff/` | Danh sách/tìm kiếm/lọc nhân viên (có phân trang) | Session | `view:user` |
| `GET`/`POST` | `/staff/create/` | Form tạo nhân viên + gán vai trò (role) | Session | `create:user` |
| `GET`/`POST` | `/staff/{id}/edit/` | Form sửa nhân viên (đổi thông tin, mật khẩu, vai trò) | Session | `update:user` |
| `POST` | `/staff/{id}/deactivate/` | Vô hiệu hoá nhân viên (không xoá cứng) | Session | `delete:user` |
| `POST` | `/staff/{id}/activate/` | Kích hoạt lại nhân viên đã vô hiệu hoá | Session | `update:user` |
| `GET` | `/staff/roles/` | Danh sách vai trò (role) kèm số quyền/số nhân viên | Session | `view:role` |
| `GET`/`POST` | `/staff/roles/create/` | Form tạo vai trò mới + chọn permission | Session | `create:role` |
| `GET`/`POST` | `/staff/roles/{id}/edit/` | Form sửa vai trò (tên, mô tả, permission) | Session | `update:role` |
| `GET` | `/products/` | Danh sách/tìm kiếm/lọc sản phẩm (có phân trang) | Session | `view:product` |
| `GET`/`POST` | `/products/create/` | Form tạo sản phẩm | Session | `create:product` |
| `GET`/`POST` | `/products/{id}/update/` | Form sửa sản phẩm (SKU không được sửa) | Session | `update:product` |
| `POST` | `/products/{id}/delete/` | Xoá mềm sản phẩm | Session | `delete:product` |
| `GET` | `/categories/` | Danh sách/tìm kiếm danh mục (có phân trang) | Session | `view:category` |
| `GET`/`POST` | `/categories/create/` | Form tạo danh mục | Session | `create:category` |
| `GET`/`POST` | `/categories/{id}/update/` | Form sửa danh mục | Session | `update:category` |
| `POST` | `/categories/{id}/delete/` | Xoá mềm danh mục nếu không còn sản phẩm tham chiếu | Session | `delete:category` |
| `GET` | `/trash/` | Thùng rác và thao tác khôi phục Product/Category | Session | Quyền Product/Category tương ứng |
| `GET` | `/inventory/` | Danh sách/tìm kiếm/lọc tồn kho (có phân trang) | Session | `view:inventory` |
| `GET` | `/inventory/{product_id}/` | Chi tiết tồn và lịch sử biến động | Session | `view:inventory` |
| `POST` | `/inventory/{product_id}/movement/` | Nhập/xuất/điều chỉnh tồn kho | Session | `create:inventory` |
| `POST` | `/inventory/{product_id}/threshold/` | Cập nhật ngưỡng tồn thấp | Session | `update:inventory` |

### JSON API Root

| Method | Endpoint | Mô tả | Auth |
|---|---|---|---|
| `GET` | `/api/v1/` | Danh mục module dạng JSON (dùng cho client gọi API, không phải trình duyệt) | Không |

### Health Check

| Method | Endpoint | Mô tả | Auth |
|---|---|---|---|
| `GET` | `/api/v1/health/` | Kiểm tra tình trạng dịch vụ | Không |

### Authentication

| Method | Endpoint | Mô tả | Auth |
|---|---|---|---|
| `POST` | `/api/v1/auth/login/` | Đăng nhập bằng email & password | Không |
| `POST` | `/api/v1/auth/logout/` | Blacklist refresh token | Có |
| `POST` | `/api/v1/auth/refresh/` | Làm mới access token | Không |
| `GET` | `/api/v1/auth/me/` | Lấy thông tin user hiện tại | Có |
| `PATCH` | `/api/v1/auth/me/` | Cập nhật thông tin user hiện tại | Có |
| `POST` | `/api/v1/auth/change-password/` | Đổi mật khẩu | Có |

### RBAC — Quản lý vai trò & quyền

| Method | Endpoint | Mô tả | Auth | Permission |
|---|---|---|---|---|
| `GET` | `/api/v1/roles/` | Danh sách vai trò (role) | Có | `view:role` |
| `POST` | `/api/v1/roles/` | Tạo vai trò mới | Có | `create:role` |
| `GET` | `/api/v1/roles/{id}/` | Chi tiết vai trò | Có | `view:role` |
| `PATCH` | `/api/v1/roles/{id}/` | Cập nhật vai trò | Có | `update:role` |
| `DELETE` | `/api/v1/roles/{id}/` | Xoá vai trò | Có | `delete:role` |
| `GET` | `/api/v1/permissions/` | Danh sách toàn bộ permission | Có | `view:role` |

### Quản lý Nhân viên (User Management)

| Method | Endpoint | Mô tả | Auth | Permission |
|---|---|---|---|---|
| `GET` | `/api/v1/users/` | Danh sách/tìm kiếm nhân viên (`?search=&is_active=&page=`) | Có | `view:user` |
| `POST` | `/api/v1/users/` | Tạo tài khoản nhân viên mới + gán vai trò (role) | Có | `create:user` |
| `GET` | `/api/v1/users/{id}/` | Chi tiết nhân viên (kèm role) | Có | `view:user` |
| `PATCH` | `/api/v1/users/{id}/` | Cập nhật thông tin/vai trò nhân viên | Có | `update:user` |
| `DELETE` | `/api/v1/users/{id}/` | Vô hiệu hoá nhân viên (`is_active=False`, không xoá cứng) | Có | `delete:user` |

### Quản lý Khách hàng (Customer Management)

| Method | Endpoint | Mô tả | Auth | Permission |
|---|---|---|---|---|
| `POST` | `/api/v1/customers/` | Tạo khách hàng | Có | `create:customer` |
| `GET` | `/api/v1/customers/` | Danh sách/tìm kiếm/lọc/sắp xếp khách hàng (có phân trang) | Có | `view:customer` |
| `GET` | `/api/v1/customers/{id}/` | Chi tiết khách hàng | Có | `view:customer` |
| `PUT` | `/api/v1/customers/{id}/` | Cập nhật khách hàng | Có | `update:customer` |
| `DELETE` | `/api/v1/customers/{id}/` | Xoá mềm khách hàng (soft delete) | Có | `delete:customer` |

Tham số query của `GET /api/v1/customers/`:

| Tham số | Mô tả |
|---|---|
| `search` | Tìm theo `customer_code`, `full_name`, `phone`, hoặc `email` (khớp một phần). |
| `status` | Lọc theo trạng thái chính xác: `active`, `inactive`, `blocked`. |
| `ordering` | Sắp xếp theo `full_name`, `customer_code`, `status`, `created_at`, `updated_at`. Thêm `-` phía trước để sắp xếp giảm dần. |
| `page`, `page_size` | Phân trang chuẩn (mặc định 20/trang, tối đa 100/trang). |

### Quản lý Sản phẩm và Danh mục (Product Management)

| Method | Endpoint | Mô tả | Auth | Permission |
|---|---|---|---|---|
| `POST` | `/api/v1/products/` | Tạo sản phẩm | Có | `create:product` |
| `GET` | `/api/v1/products/` | Danh sách/tìm kiếm/lọc/sắp xếp sản phẩm (có phân trang) | Có | `view:product` |
| `GET` | `/api/v1/products/{id}/` | Chi tiết sản phẩm | Có | `view:product` |
| `PUT`/`PATCH` | `/api/v1/products/{id}/` | Cập nhật sản phẩm (SKU không được sửa) | Có | `update:product` |
| `DELETE` | `/api/v1/products/{id}/` | Xoá mềm sản phẩm | Có | `delete:product` |
| `POST` | `/api/v1/categories/` | Tạo danh mục | Có | `create:category` |
| `GET` | `/api/v1/categories/` | Danh sách/tìm kiếm danh mục (có phân trang) | Có | `view:category` |
| `GET` | `/api/v1/categories/{id}/` | Chi tiết danh mục | Có | `view:category` |
| `PUT`/`PATCH` | `/api/v1/categories/{id}/` | Cập nhật danh mục | Có | `update:category` |
| `DELETE` | `/api/v1/categories/{id}/` | Xoá mềm danh mục nếu không còn sản phẩm tham chiếu | Có | `delete:category` |

Tham số query của `GET /api/v1/products/`:

| Tham số | Mô tả |
|---|---|
| `search` | Tìm theo `sku`, `name` hoặc `description` (khớp một phần). |
| `status` | Lọc theo trạng thái `active` hoặc `inactive`. |
| `category` | Lọc theo UUID của danh mục. |
| `ordering` | Sắp xếp theo trường được hỗ trợ; thêm `-` phía trước để giảm dần. |
| `page`, `page_size` | Phân trang chuẩn của dự án. |

### Quản lý Kho (Inventory Management)

| Method | Endpoint | Mô tả | Auth | Permission |
|---|---|---|---|---|
| `GET` | `/api/v1/inventory/` | Danh sách tồn hiện tại theo Product | Có | `view:inventory` |
| `GET` | `/api/v1/inventory/{product_id}/` | Chi tiết tồn của một Product | Có | `view:inventory` |
| `PATCH` | `/api/v1/inventory/{product_id}/threshold/` | Cập nhật ngưỡng cảnh báo tồn thấp | Có | `update:inventory` |
| `GET` | `/api/v1/inventory/movements/` | Lịch sử biến động (có phân trang) | Có | `view:inventory` |
| `POST` | `/api/v1/inventory/movements/` | Nhập, xuất hoặc điều chỉnh số tồn | Có | `create:inventory` |

Tham số query:

| Endpoint | Tham số |
|---|---|
| `GET /api/v1/inventory/` | `search`, `product__category`, `product__status`, `ordering`, `page`, `page_size` |
| `GET /api/v1/inventory/movements/` | `search`, `inventory__product`, `movement_type`, `ordering`, `page`, `page_size` |

Quy ước `POST /api/v1/inventory/movements/`: `quantity` của `inbound`/`outbound` là lượng thay đổi dương; `quantity` của `adjustment` là số tồn mục tiêu. Mọi thay đổi được ghi thành StockMovement bất biến và không cho phép tồn âm.

### Định dạng Response API

**Thành công:**
```json
{
  "success": true,
  "message": "...",
  "data": { }
}
```

**Lỗi:**
```json
{
  "success": false,
  "message": "...",
  "errors": { }
}
```

## Quy tắc Coding & Triển khai

Đây là **cẩm nang quy tắc chuẩn** cho việc mở rộng codebase này — dành cho cả
dev lẫn AI agent. Mục này hệ thống hoá lại cách đã làm ở `apps/accounts`
(Sprint 1) và `apps/customers` (Sprint 2). Hãy tuân theo **chính xác** khi thêm
module mới (Product, Inventory, Order, Invoice, Payment, ...), trừ khi task
yêu cầu khác đi một cách tường minh.

> Trước khi có prompt kỹ thuật, module mới nên bắt đầu từ một PRD (Product
> Requirements Document) theo [`docs/template-PRD.md`](docs/template-PRD.md) —
> mô tả bài toán nghiệp vụ, actor, entity, chức năng ở mức yêu cầu, chưa động
> đến kiến trúc code. Khi PRD được duyệt, convert sang prompt kỹ thuật theo
> template chuẩn tại [`docs/prompt-features.md`](docs/prompt-features.md) —
> file đó tham chiếu ngược lại đúng các quy tắc trong mục này để đảm bảo mọi
> tính năng được yêu cầu và triển khai theo cùng một khuôn.

### 1. Kiến trúc phân lớp — phụ thuộc một chiều, không đi tắt

```
View (thin) → Serializer → Service → Selector → ORM → PostgreSQL
```

| Layer | Được làm | Không bao giờ làm |
|---|---|---|
| **View** | Parse request, gọi 1 serializer, gọi 1 service/selector, trả về `success_response`/`error_response` | Business logic, query ORM trực tiếp, trả `Response` thô |
| **Serializer** | Validate field/object (`validate_<field>`, `validate`), định dạng output | Ghi/sửa DB, các rule nghiệp vụ phụ thuộc nhiều hơn dữ liệu field |
| **Service** | Business logic, điều phối, toàn bộ thao tác ghi (`create`/`update`/`delete`), `@transaction.atomic` khi đụng nhiều bảng/dòng | Trả HTTP response, parse object `request` |
| **Selector** | Truy vấn read-only, mỗi model 1 class (`<Model>Selector`), trả về queryset / instance / `None` | Raise exception, ghi/sửa dữ liệu |
| **Model** | Field, `Meta`, property tính toán đơn giản (`__str__`, computed property) | Logic truy vấn, rule nghiệp vụ liên model |

View **không bao giờ** gọi thẳng `Model.objects` — luôn phải đi qua Selector
(đọc) hoặc Service (ghi).

### 2. Cấu trúc file mỗi app — không được sai khác

```
apps/<tên_app>/
├── __init__.py
├── apps.py            # AppConfig
├── admin.py            # Đăng ký với Django admin
├── constants.py        # TextChoices enum + hằng số MSG_*
├── exceptions.py       # Các class kế thừa ApplicationError, mỗi lỗi nghiệp vụ 1 class
├── managers.py          # Custom model manager (chỉ khi model thực sự cần)
├── models.py             # ORM model
├── permissions.py        # Hằng số dict action/resource cho RBAC của app này
├── selectors.py           # Truy vấn read-only — mỗi model 1 class: `<Model>Selector`
├── serializers.py          # `Create*`, `Update*`, `*ListSerializer`, `*DetailSerializer`
├── services.py              # Business logic — mỗi model 1 class: `<Model>Service`
├── urls.py                  # Danh sách path(); bắt buộc set `app_name = "<tên_app>"`
├── validators.py              # Validator dùng chung giữa model + serializer
├── views.py                   # Class kế thừa APIView / GenericAPIView
├── migrations/
└── tests/
    ├── __init__.py
    └── test_*.py
```

### 3. Response envelope — không được phá vỡ

Mọi endpoint đều trả về `shared.response.success_response()` hoặc
`error_response()`. Lỗi nghiệp vụ được raise dưới dạng class kế thừa
`ApplicationError` (khai báo trong `exceptions.py` của app) —
`shared.exceptions.custom_exception_handler` (đã cấu hình toàn cục qua
`REST_FRAMEWORK.EXCEPTION_HANDLER`) sẽ tự động chuyển thành envelope lỗi
chuẩn. Không tự format dict lỗi trong view.

### 4. RBAC — tái sử dụng, không viết lại

- Mọi kiểm tra quyền đều đi qua `apps.accounts.permissions.HasPermission`.
  Không viết thêm permission class riêng cho từng app.
- Nếu resource của bạn chưa có trong `PermissionResource`
  (`apps/accounts/constants.py`), thêm vào đó — đây là **ngoại lệ duy nhất**
  được phép sửa `apps/accounts`. Không đụng vào phần nào khác trong
  `apps/accounts`.
- Khai báo hằng số dict `{"action": ..., "resource": ...}` trong file
  `permissions.py` của app mình (xem `apps/customers/permissions.py`). Không
  hardcode permission dict trực tiếp trong view.
- Với view xử lý nhiều HTTP method có permission khác nhau (list+create,
  detail/update/delete), set `self.required_permission` theo từng method bằng
  cách override `check_permissions()` — xem `RoleListCreateView` /
  `CustomerListCreateView` làm mẫu. Superuser luôn bypass RBAC
  (`PermissionSelector.user_has_permission`).

### 5. Soft delete cho các resource được tham chiếu

Resource nào bị module khác foreign-key tới (Customer hiện tại; Product,
Order, Invoice ở sprint sau) đều phải xoá mềm, không được `DELETE` cứng:

- Field: `is_deleted = models.BooleanField(default=False)`,
  `deleted_at = models.DateTimeField(null=True, blank=True)`.
- Manager mặc định (`objects`) tự động loại bỏ dòng đã xoá mềm (xem
  `apps/customers/managers.py::CustomerManager`). Thêm manager thứ hai
  `all_objects = models.Manager()` để admin/audit xem được toàn bộ, và để
  kiểm tra tính duy nhất (unique constraint ở DB là toàn bảng, nên chỉ check
  qua `objects` có thể bỏ sót một dòng đã bị xoá mềm nhưng vẫn đụng unique).
- `Service.delete_*()` chỉ set 2 field trên rồi save — không bao giờ gọi
  `.delete()`.

### 6. Quy tắc Validation

- Kiểm tra tính duy nhất/định dạng thuộc về serializer (`validate_<field>`),
  dựa trên helper `Selector.<x>_exists()` — không dựa vào
  `try/except IntegrityError` làm hướng xử lý chính (DB constraint chỉ là lớp
  chặn cuối, không phải là UX chính).
- Serializer cập nhật (Update) nhận `context={"<model>_id": ...}` để loại trừ
  chính bản ghi đang sửa khi check unique (xem `UpdateCustomerSerializer`).
- Field kiểu enum dùng `serializers.ChoiceField(choices=<TextChoices>.choices)`
  — không dùng `CharField` thường cho field được backing bởi `TextChoices`.

### 7. Phân trang, tìm kiếm, lọc, sắp xếp

Endpoint list kế thừa `GenericAPIView` (không dùng `APIView` thường) và dùng
`shared.pagination.paginated_success_response(view, queryset, serializer_class)`.
Khai báo `filterset_fields`, `search_fields`, `ordering_fields`, `ordering` là
class attribute — 3 backend (`DjangoFilterBackend`, `SearchFilter`,
`OrderingFilter`) đã được cấu hình toàn cục qua
`REST_FRAMEWORK.DEFAULT_FILTER_BACKENDS`. Không tự viết lại logic phân
trang/lọc trong view.

### 8. Testing

- Mỗi app 1 file test: `apps/<app>/tests/test_*.py`, dùng `pytest` +
  `pytest-django`. Mỗi test đều có comment `# Arrange` / `# Act` / `# Assert`
  (mẫu AAA).
- Tối thiểu phải cover: ràng buộc của model, mọi method của selector, mọi
  method của service (cả trường hợp thành công lẫn not-found/lỗi), và mọi
  endpoint (có permission / không có permission / superuser bypass).
- Fixture chỉ được thêm vào `tests/conftest.py` ở **root project** — không
  tạo `conftest.py` riêng cho từng app. File `conftest.py` ở gốc re-export lại
  toàn bộ từ `tests/conftest.py` (`from tests.conftest import *`) vì pytest
  chỉ tự động chia sẻ fixture của một `conftest.py` cho các test nằm trong
  chính thư mục con của nó, mà `tests/` và `apps/*/tests/` là hai thư mục anh
  em (sibling), không phải cha-con. Nếu thêm fixture, chỉ cần thêm vào
  `tests/conftest.py` — không bao giờ cần sửa `conftest.py` ở gốc.
- Chạy bằng `docker compose exec backend pytest --cov`. Ngưỡng coverage tối
  thiểu là 80% (`pyproject.toml → [tool.coverage.report] → fail_under`).

### 9. Style & Tooling

Format bằng `black` (88 ký tự/dòng), lint bằng `ruff` (rule set khai báo
trong `pyproject.toml`), sort import bằng `isort` (`profile = "black"`). Chạy
trước khi mở PR:

```bash
docker compose exec backend black .
docker compose exec backend ruff check .
docker compose exec backend mypy .
```

- Mọi class/function public đều phải có docstring (chuẩn Google —
  `Args:`/`Returns:`/`Raises:`). Không viết comment giải thích lại *cái gì*
  code đang làm; chỉ comment *tại sao*, và chỉ khi thực sự không hiển nhiên.
- Nợ kỹ thuật lint đã biết trước: `RUF012` (mutable default cho class
  attribute — `permission_classes` của DRF, `Meta.ordering`/`indexes` của
  Django, `dependencies`/`operations` trong migration) chưa được fix toàn bộ
  codebase. Không chặn PR vì lỗi này, và cũng không tiện tay fix ở file không
  liên quan — nhưng cũng không được tạo ra một *loại lỗi lint mới*.

### 10. Checklist — thêm module cho sprint mới

0. Viết PRD theo [`docs/template-PRD.md`](docs/template-PRD.md), review &
   duyệt trước khi đụng tới code hay viết prompt kỹ thuật.
1. Convert PRD đã duyệt thành prompt kỹ thuật theo
   [`docs/prompt-features.md`](docs/prompt-features.md), rồi tạo `apps/<tên>/`
   theo đúng cấu trúc ở mục 2.
2. Đăng ký: thêm vào `LOCAL_APPS` trong `config/settings/base.py`, và
   `path("api/v1/", include("apps.<tên>.urls"))` trong `config/urls.py`.
3. Nếu resource cần RBAC, thêm vào `PermissionResource`
   (`apps/accounts/constants.py`) — chỉnh sửa duy nhất được phép trong
   `apps/accounts`.
4. `docker compose exec backend python manage.py makemigrations <tên>` rồi
   `migrate`.
5. Viết test + fixture; chạy `pytest --cov`, `black .`, `ruff check .`.
6. Cập nhật bảng API trong README (mục "Tài liệu API" ở trên, và cả
   `config/views.py::FEATURE_MODULES` nếu module có endpoint public) và tạo
   `docs/sprint_N.md` (xem `docs/sprint_1.md` / `docs/sprint_2.md` để biết cấu
   trúc chuẩn: Summary → What Was Built → Design Decisions → Files Changed →
   Next Sprint). Đối chiếu lại với PRD gốc ở bước 0 — nêu rõ nếu có sai lệch
   phạm vi so với PRD.
7. Nếu module cần một màn hình HTML trong `apps/dashboard` (không chỉ JSON
   API), làm theo mục 11 ngay dưới đây — không tạo lại session auth hay
   permission-check logic riêng.

### 11. Giao diện quản trị (Dashboard UI) — `apps/dashboard`

`apps/dashboard` là lớp trình bày HTML, dùng **session** (khác JWT của
`/api/v1/...`), cho phép user thường đăng nhập và thao tác theo đúng RBAC đã
được gán — không phải Django Admin (vốn yêu cầu `is_staff=True`). Khi thêm màn
hình HTML cho một module mới (vd. Product), áp dụng đúng các quy tắc 1-9 ở
trên, cộng thêm:

- **Form thay cho Serializer.** Input validation của một view HTML nằm trong
  một Django `forms.Form` (xem `apps/dashboard/forms.py::CustomerForm`) —
  cùng vai trò với Serializer ở API, và **tái sử dụng chính các helper đã có**
  (`Selector.<x>_exists()`, `is_valid_phone_number()`, ...) để hai transport
  không bao giờ chấp nhận hai bộ dữ liệu khác nhau.
- **`require_permission(action, resource)` thay cho `HasPermission`.**
  DRF's `HasPermission` là một `BasePermission`, gắn với vòng đời request của
  DRF nên không dùng trực tiếp cho view HTML thường được. Decorator
  `apps.dashboard.decorators.require_permission` là bản tương đương, nhưng gọi
  **chung** `PermissionSelector.user_has_permission` — RBAC chỉ định nghĩa một
  lần, hai transport enforce giống hệt nhau.
- **View vẫn thin.** `views.py` trong `apps/dashboard` gọi thẳng
  `<Model>Selector`/`<Model>Service` của app nghiệp vụ tương ứng (vd.
  `apps.customers.selectors.CustomerSelector`), không tự viết business logic
  hay query ORM trực tiếp — giống hệt quy tắc ở mục 1.
- **Selector có thể cần thêm một method non-DRF.** DRF dùng
  `filter_backends` để search/filter/sort; view HTML thường không có DRF
  backends, nên Selector cần một method trả về queryset đã lọc sẵn bằng
  `Q()` (xem `CustomerSelector.search_customers`). Đây là method riêng, KHÔNG
  thay thế cách `get_all_customers()` + DRF filter backend đang được dùng ở
  API — cả hai cùng tồn tại, phục vụ hai transport khác nhau.
- Template nằm ở `apps/dashboard/templates/dashboard/<app>/*.html`, style dùng
  chung `apps/dashboard/static/dashboard/style.css` (không thêm framework CSS/JS
  mới cho một module riêng lẻ).
- Test session-based dùng fixture `client` có sẵn của `pytest-django`
  (`client.login(email=..., password=...)`) — **không** dùng
  `APIClient.force_authenticate`, vì nó chỉ gắn `request.user` cho request DRF,
  không tạo session thật cho view Django thường.

> Chi tiết hoá quy trình trên thành một **prompt chuẩn** (dùng để giao task
> cho AI agent hoặc brief cho dev khác) nằm ở
> [`docs/prompt-features.md`](docs/prompt-features.md) — hãy dùng file đó mỗi
> khi bắt đầu một tính năng/module mới để đảm bảo tất cả thành viên trong team
> mô tả yêu cầu theo cùng một khuôn, tránh thiếu sót.

## Các lệnh Development

```bash
# Chạy test
docker compose exec backend pytest

# Chạy test kèm coverage
docker compose exec backend pytest --cov

# Format code
docker compose exec backend black .

# Lint
docker compose exec backend ruff check .

# Type check
docker compose exec backend mypy .

# Tạo superuser
docker compose exec backend python manage.py createsuperuser

# Tạo migration
docker compose exec backend python manage.py makemigrations

# Áp dụng migration
docker compose exec backend python manage.py migrate
```

## Biến môi trường

Xem [.env.example](.env.example) để biết toàn bộ cấu hình khả dụng.

## Tài liệu liên quan

| Tài liệu | Mục đích |
|---|---|
| [`docs/template-PRD.md`](docs/template-PRD.md) | Template mô tả yêu cầu sản phẩm (PRD) — điền **trước** khi viết prompt kỹ thuật cho module mới. |
| [`docs/prompt-features.md`](docs/prompt-features.md) | Template & quy tắc viết prompt chuẩn khi triển khai một tính năng/module mới. |
| [`docs/sprint_0.md`](docs/sprint_0.md) | Hạ tầng nền tảng (Docker, Django, response envelope). |
| [`docs/sprint_1.md`](docs/sprint_1.md) | Authentication (JWT) & RBAC. |
| [`docs/sprint_2.md`](docs/sprint_2.md) | Customer Management (module tham chiếu chuẩn cho các sprint sau). |
| [`docs/prd_product.md`](docs/prd_product.md) | Đặc tả nghiệp vụ Product/Category và hợp đồng tích hợp Inventory. |
| [`docs/sprint_3.md`](docs/sprint_3.md) | Product Management và nền dữ liệu cho Inventory. |
| [`docs/prd_inventory.md`](docs/prd_inventory.md) | Đặc tả nghiệp vụ, database và hợp đồng giao dịch Inventory. |
| [`docs/sprint_4.md`](docs/sprint_4.md) | Inventory Management, sổ biến động và kiểm soát đồng thời. |

## License

Dự án thuộc chương trình đồ án tốt nghiệp (capstone) tại UIT.
