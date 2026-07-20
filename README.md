# POS Management System

> Hệ thống quản lý bán hàng (Point of Sale - POS) tích hợp thanh toán trực tuyến qua SePay và AI hỗ trợ phân tích kinh doanh.

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Django](https://img.shields.io/badge/Django-5.x-green)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-blue)
![JWT](https://img.shields.io/badge/Auth-JWT-orange)
![AI](https://img.shields.io/badge/AI-Gemini%20%7C%20GPT-purple)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 1. Giới thiệu

**POS Management System** là một hệ thống quản lý bán hàng được xây dựng bằng Python và Django.

Hệ thống hỗ trợ các nghiệp vụ cơ bản của một hệ thống POS:

- Quản lý người dùng và nhân viên.
- Quản lý khách hàng.
- Quản lý sản phẩm và danh mục.
- Quản lý tồn kho.
- Tạo và quản lý hóa đơn.
- Thanh toán tiền mặt và thanh toán trực tuyến.
- Tích hợp SePay thông qua API và Webhook.
- Báo cáo doanh thu.
- Ghi nhận lịch sử hoạt động của người dùng.
- Sử dụng AI để phân tích dữ liệu kinh doanh và đưa ra các khuyến nghị.

---

## 2. Mục tiêu dự án

Dự án được xây dựng với các mục tiêu:

1. Xây dựng một hệ thống POS có quy trình bán hàng hoàn chỉnh.
2. Áp dụng Python và Django để xây dựng hệ thống Web/API.
3. Thiết kế hệ thống cơ sở dữ liệu quan hệ với PostgreSQL.
4. Tích hợp thanh toán trực tuyến thông qua SePay.
5. Xử lý thanh toán bất đồng bộ thông qua Webhook.
6. Áp dụng JWT Authentication và phân quyền người dùng.
7. Xây dựng báo cáo và Dashboard.
8. Tích hợp AI để phân tích dữ liệu kinh doanh.
9. Áp dụng các nguyên tắc phát triển phần mềm và quản lý dự án Agile/Scrum.

---

# 3. Chức năng hệ thống

## 3.1 Authentication

- Đăng nhập.
- Đăng xuất.
- JWT Authentication.
- Refresh Token.
- Xác thực API.
- Kiểm tra quyền truy cập.

---

## 3.2 Quản lý người dùng

Hệ thống hỗ trợ các loại người dùng:

### Admin

- Quản lý người dùng.
- Quản lý sản phẩm.
- Quản lý khách hàng.
- Xem báo cáo.
- Xem Audit Log.

### Staff

- Quản lý khách hàng.
- Tạo hóa đơn.
- Thực hiện thanh toán.
- Xem lịch sử giao dịch.

---

## 3.3 Quản lý khách hàng

- Thêm khách hàng.
- Cập nhật thông tin khách hàng.
- Xóa khách hàng.
- Xem thông tin Profile.
- Xem lịch sử hóa đơn.
- Theo dõi lịch sử mua hàng.
- Tích điểm khách hàng (Optional).

---

## 3.4 Quản lý sản phẩm

- Quản lý danh mục sản phẩm.
- Thêm sản phẩm.
- Cập nhật sản phẩm.
- Xóa sản phẩm.
- Quản lý giá bán.
- Quản lý VAT.
- Quản lý mã sản phẩm.
- Quản lý trạng thái sản phẩm.

---

## 3.5 Quản lý tồn kho

Hệ thống hỗ trợ:

- Theo dõi số lượng tồn kho.
- Nhập kho.
- Xuất kho.
- Điều chỉnh số lượng tồn kho.
- Lịch sử thay đổi tồn kho.
- Cảnh báo sản phẩm sắp hết hàng.

### Quy tắc nghiệp vụ

```text
Stock hiện tại = 100

Bán 2 sản phẩm

Stock còn lại = 98

## Coding Convention

All project code must follow the rules defined in:

[coding-convention.md](./coding-convention.md)