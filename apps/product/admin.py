import os
from django import forms
from django.contrib import admin, messages
from django.db import IntegrityError
from django.db.models import Count, ProtectedError, Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.html import format_html

# Sửa dòng import ở đầu file apps/product/admin.py
from apps.product.models import Category, Product, CategoryTrash, ProductTrash


def _format_vnd(value):
    """Hiển thị giá có dấu phẩy, ví dụ: 1,000,000đ"""
    if value is None:
        return "—"
    try:
        return f"{int(value):,}đ"
    except (TypeError, ValueError):
        return str(value)


def _format_user(user):
    if not user:
        return "—"
    return user.full_name or user.email


def _format_user_datetime(user, dt):
    person = _format_user(user)
    when = timezone.localtime(dt).strftime("%d/%m/%Y %H:%M") if dt else "—"
    return format_html("{}<br><small style='color:#666'>{}</small>", person, when)


def _format_uuid(obj_id):
    if not obj_id:
        return "—"
    return format_html('<small style="color:#666;font-family:monospace">{}</small>', obj_id)


def _sku_with_uuid_display(obj):
    return format_html(
        '<strong>{}</strong><br><small style="color:#666;font-family:monospace">{}</small>',
        obj.sku,
        obj.id,
    )


def _image_preview_display(obj):
    if obj.image and hasattr(obj.image, "url"):
        try:
            if os.path.exists(obj.image.path):
                return format_html(
                    '<img src="{}" style="width: 45px; height: 45px; object-fit: cover; border-radius: 4px;" />',
                    obj.image.url,
                )
        except Exception:
            pass
    return "—"


# PRODUCT_TXN_GUARD — chặn xóa hẳn SP đã có giao dịch (logic gốc: Product.has_transaction_history)
HARD_DELETE_BLOCKED_MSG = (
    "KHÔNG THỂ XÓA HẲN! Sản phẩm '{name}' đã phát sinh lịch sử giao dịch "
    "(Kho hàng, Đơn hàng hoặc Hóa đơn)."
)


def _hard_delete_products(request, queryset):
    """PRODUCT_TXN_GUARD: xóa vĩnh viễn — gọi từ ProductTrashAdmin."""
    success_count = 0
    blocked_count = 0
    failed_count = 0

    for obj in queryset:
        if obj.has_transaction_history():
            blocked_count += 1
            continue
        try:
            obj.delete()
            success_count += 1
        except (ProtectedError, IntegrityError):
            failed_count += 1

    if success_count > 0:
        messages.success(request, f"Đã xóa vĩnh viễn {success_count} sản phẩm.")
    if blocked_count > 0:
        messages.error(
            request,
            f"Có {blocked_count} sản phẩm không thể xóa hẳn vì đã phát sinh giao dịch "
            f"(Kho hàng, Đơn hàng hoặc Hóa đơn).",
        )
    if failed_count > 0:
        messages.error(
            request,
            f"Có {failed_count} sản phẩm không thể xóa hẳn do ràng buộc dữ liệu trong CSDL.",
        )


class CategoryHasProductsFilter(admin.SimpleListFilter):
    title = "Sản phẩm"
    parameter_name = "has_products"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Có sản phẩm"),
            ("no", "Danh mục trống"),
        )

    def queryset(self, request, queryset):
        active_category_ids = Product.objects.filter(
            deleted_at__isnull=True,
            category__isnull=False,
        ).values_list("category_id", flat=True).distinct()

        if self.value() == "yes":
            return queryset.filter(id__in=active_category_ids)
        if self.value() == "no":
            return queryset.exclude(id__in=active_category_ids)
        return queryset


# ==============================================================================
# FORM
# ==============================================================================
class ProductAdminForm(forms.ModelForm):
    # CharField để nhận dấu phẩy khi nhập (vd: 1,000,000) mà không lỗi validation
    cost_price = forms.CharField(
        label="Giá nhập",
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "vTextField currency-input",
                "placeholder": "1,000",
                "autocomplete": "off",
            }
        ),
    )
    selling_price = forms.CharField(
        label="Giá bán",
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "vTextField currency-input",
                "placeholder": "1,200",
                "autocomplete": "off",
            }
        ),
        help_text="Tự gợi ý = Giá nhập × 1.2 khi bạn nhập giá nhập (có thể sửa lại).",
    )

    class Meta:
        model = Product
        fields = "__all__"

    class Media:
        js = ("admin/js/product_price.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hiển thị dấu phẩy khi sửa sản phẩm đã có
        if self.instance and self.instance.pk:
            if self.instance.cost_price is not None:
                self.initial["cost_price"] = f"{int(self.instance.cost_price):,}"
            if self.instance.selling_price is not None:
                self.initial["selling_price"] = f"{int(self.instance.selling_price):,}"
            self.fields["sku"].disabled = True
            self.fields["sku"].help_text = "Mã SP/SKU không thể thay đổi"

    def clean_sku(self):
        if self.instance and self.instance.pk:
            return self.instance.sku
        sku = self.cleaned_data.get("sku")
        if not sku:
            raise forms.ValidationError("Vui lòng nhập Mã sản phẩm.")
        return sku

    def _parse_price(self, raw, field_label):
        val_str = str(raw or "").replace(",", "").strip()
        if not val_str:
            raise forms.ValidationError(f"Vui lòng nhập {field_label}.")
        try:
            val = float(val_str)
        except ValueError:
            raise forms.ValidationError(f"{field_label} không hợp lệ.")
        if val < 1:
            raise forms.ValidationError(f"{field_label} phải lớn hơn hoặc bằng 1.")
        return val

    def clean_cost_price(self):
        return self._parse_price(self.cleaned_data.get("cost_price"), "Giá nhập")

    def clean_selling_price(self):
        return self._parse_price(self.cleaned_data.get("selling_price"), "Giá bán")

    def clean(self):
        cleaned_data = super().clean()
        cost_price = cleaned_data.get("cost_price")
        selling_price = cleaned_data.get("selling_price")
        if cost_price is not None and selling_price is not None:
            if selling_price <= cost_price:
                self.add_error("selling_price", "Giá bán phải lớn hơn giá nhập.")
        return cleaned_data


# ==============================================================================
# CATEGORY ADMIN
# ==============================================================================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    change_list_template = "admin/product/category/change_list.html"
    list_display = (
        "uuid_display",
        "name",
        "description",
        "product_count",
        "created_info",
        "updated_info",
    )
    list_filter = (
        CategoryHasProductsFilter,
        "created_by",
        "updated_by",
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = ("name", "description", "id")
    exclude = ("created_by", "updated_by", "deleted_at", "created_at", "updated_at")
    actions = ["move_to_trash"]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("uuid_display",)
        return ()

    # 1. Chỉ hiển thị danh mục chưa xóa mềm
    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(deleted_at__isnull=True)
            .annotate(
                active_product_count=Count(
                    "products",
                    filter=Q(products__deleted_at__isnull=True),
                )
            )
            .select_related("created_by", "updated_by")
        )

    # 2. Bỏ action "Delete selected..." mặc định
    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    # 3. Action chuyển vào thùng rác (Có kiểm tra sản phẩm đang hoạt động)
    @admin.action(description="Chuyển vào thùng rác")
    def move_to_trash(self, request, queryset):
        success_count = 0
        failed_count = 0
        for cat in queryset:
            if cat.products.filter(deleted_at__isnull=True).exists():
                failed_count += 1
            else:
                cat.deleted_at = timezone.now()
                if request.user.is_authenticated:
                    cat.updated_by = request.user
                cat.save()
                success_count += 1

        if success_count > 0:
            self.message_user(request, f"Đã chuyển {success_count} danh mục vào thùng rác.")
        if failed_count > 0:
            self.message_user(
                request,
                f"Có {failed_count} danh mục không thể xóa vì vẫn còn chứa sản phẩm đang hoạt động!",
                level=messages.WARNING,
            )

    # 4. Ghi đè nút Xóa 1 danh mục trong trang chi tiết
    def delete_model(self, request, obj):
        if obj.products.filter(deleted_at__isnull=True).exists():
            messages.error(
                request,
                f"Không thể xóa! Danh mục '{obj.name}' vẫn còn sản phẩm đang hoạt động."
            )
            return
        obj.deleted_at = timezone.now()
        if request.user.is_authenticated:
            obj.updated_by = request.user
        obj.save()

    @admin.display(description="Số sản phẩm", ordering="active_product_count")
    def product_count(self, obj):
        return obj.active_product_count

    @admin.display(description="SKU/UUID", ordering="id")
    def uuid_display(self, obj):
        return _format_uuid(obj.id)

    uuid_display.short_description = "UUID"

    @admin.display(description="Create By", ordering="created_at")
    def created_info(self, obj):
        return _format_user_datetime(obj.created_by, obj.created_at)

    @admin.display(description="Update By", ordering="updated_at")
    def updated_info(self, obj):
        return _format_user_datetime(obj.updated_by, obj.updated_at)

    def save_model(self, request, obj, form, change):
        if not change or not obj.created_by_id:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Mô tả")
    def description_short(self, obj):
        if not obj.description:
            return "—"

        text = obj.description.strip()
        return format_html(
            '<div title="{}" style="max-width: 100px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #4a5568; font-size: 13px;">{}</div>',
            text,
            text,
        )

# ==============================================================================
# PRODUCT ADMIN
# ==============================================================================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    change_list_template = "admin/product/product/change_list.html"

    list_display = (
        "sku_with_uuid",
        "image_preview",
        "name",
        "description_short",
        "category",
        "unit",
        "cost_price_display",
        "selling_price_display",
        "status",
        "created_info",
        "updated_info",
    )

    list_filter = ("status", "category", "unit")
    search_fields = ("sku", "name", "description", "id")
    exclude = ("created_by", "updated_by", "deleted_at", "created_at", "updated_at")
    actions = ["move_to_trash"]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("uuid_display",)
        return ()

    # 1. Chỉ hiển thị sản phẩm đang hoạt động
    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(deleted_at__isnull=True)
            .select_related("created_by", "updated_by", "category")
        )

    # 2. Bỏ action "Delete selected..." mặc định
    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    # 3. Action "Chuyển vào thùng rác" hàng loạt
    @admin.action(description="Chuyển vào thùng rác")
    def move_to_trash(self, request, queryset):
        count = queryset.update(deleted_at=timezone.now())
        self.message_user(request, f"Đã chuyển {count} sản phẩm vào thùng rác.")

    # 4. Ghi đè nút Xóa trong trang sửa chi tiết
    def delete_model(self, request, obj):
        obj.deleted_at = timezone.now()
        if request.user.is_authenticated:
            obj.updated_by = request.user
        obj.save()

    def image_preview(self, obj):
        return _image_preview_display(obj)

    image_preview.short_description = "Hình ảnh"

    @admin.display(description="Mã / UUID", ordering="sku")
    def sku_with_uuid(self, obj):
        return _sku_with_uuid_display(obj)

    @admin.display(description="Mô tả")
    def description_short(self, obj):
        if not obj.description:
            return "—"

        text = obj.description.strip()
        return format_html(
            '<div title="{}" style="max-width: 100px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #4a5568; font-size: 13px;">{}</div>',
            text,
            text,
        )

    @admin.display(description="UUID", ordering="id")
    def uuid_display(self, obj):
        return _format_uuid(obj.id)

    uuid_display.short_description = "UUID"

    @admin.display(description="Giá nhập", ordering="cost_price")
    def cost_price_display(self, obj):
        return _format_vnd(obj.cost_price)

    @admin.display(description="Giá bán", ordering="selling_price")
    def selling_price_display(self, obj):
        return _format_vnd(obj.selling_price)

    @admin.display(description="Create By", ordering="created_at")
    def created_info(self, obj):
        return _format_user_datetime(obj.created_by, obj.created_at)

    @admin.display(description="Update By", ordering="updated_at")
    def updated_info(self, obj):
        return _format_user_datetime(obj.updated_by, obj.updated_at)

    def save_model(self, request, obj, form, change):
        if not change or not obj.created_by_id:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CategoryTrash)
class CategoryTrashAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "deleted_at", "updated_by")
    search_fields = ("name", "description")
    actions = ["restore_from_trash", "hard_delete_selected"]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(deleted_at__isnull=False)

    def has_add_permission(self, request):
        return False

    def get_model_perms(self, request):
        # Ẩn khỏi menu sidebar — vào qua nút 🗑 cạnh Add
        return {}

    @admin.action(description="Khôi phục danh mục")
    def restore_from_trash(self, request, queryset):
        updated = queryset.update(deleted_at=None)
        self.message_user(request, f"Đã khôi phục {updated} danh mục.")

    @admin.action(description="Xóa VĨNH VIỄN khỏi CSDL")
    def hard_delete_selected(self, request, queryset):
        success_count = 0
        failed_count = 0
        for obj in queryset:
            if obj.products.exists():
                failed_count += 1
            else:
                obj.delete()
                success_count += 1

        if success_count > 0:
            self.message_user(request, f"Đã xóa vĩnh viễn {success_count} danh mục.")
        if failed_count > 0:
            self.message_user(
                request,
                f"Có {failed_count} danh mục không thể xóa vì còn sản phẩm liên kết!",
                level=messages.ERROR,
            )


@admin.register(ProductTrash)
class ProductTrashAdmin(admin.ModelAdmin):
    """Thùng rác sản phẩm. PRODUCT_TXN_GUARD: xóa hẳn qua _hard_delete_products()."""
    list_display = (
        "sku_with_uuid",
        "image_preview",
        "name",
        "category",
        "cost_price_display",
        "selling_price_display",
        "deleted_at",
        "updated_by",
    )
    search_fields = ("sku", "name")
    actions = ["restore_from_trash", "hard_delete_selected"]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(deleted_at__isnull=False)

    def has_add_permission(self, request):
        return False

    def get_model_perms(self, request):
        # Ẩn khỏi menu sidebar — vào qua nút 🗑 cạnh Add
        return {}

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    @admin.action(description="Khôi phục sản phẩm")
    def restore_from_trash(self, request, queryset):
        updated = queryset.update(deleted_at=None)
        self.message_user(request, f"Đã khôi phục {updated} sản phẩm.")

    @admin.action(description="Xóa VĨNH VIỄN khỏi CSDL")
    def hard_delete_selected(self, request, queryset):
        _hard_delete_products(request, queryset)

    def delete_model(self, request, obj):
        if obj.has_transaction_history():
            messages.error(request, HARD_DELETE_BLOCKED_MSG.format(name=obj.name))
            return
        try:
            obj.delete()
            messages.success(request, f"Đã xóa vĩnh viễn sản phẩm '{obj.name}'.")
        except (ProtectedError, IntegrityError):
            messages.error(
                request,
                f"KHÔNG THỂ XÓA HẲN! Sản phẩm '{obj.name}' đang có ràng buộc dữ liệu trong CSDL.",
            )

    def delete_queryset(self, request, queryset):
        _hard_delete_products(request, queryset)

    def image_preview(self, obj):
        return _image_preview_display(obj)

    image_preview.short_description = "Hình ảnh"

    @admin.display(description="Mã / UUID", ordering="sku")
    def sku_with_uuid(self, obj):
        return _sku_with_uuid_display(obj)

    @admin.display(description="Giá nhập", ordering="cost_price")
    def cost_price_display(self, obj):
        return _format_vnd(obj.cost_price)

    @admin.display(description="Giá bán", ordering="selling_price")
    def selling_price_display(self, obj):
        return _format_vnd(obj.selling_price)