from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import  Count, Q, ProtectedError
from django.db.models.functions import Lower
from django.core.paginator import Paginator
from django.db import IntegrityError  # Import IntegrityError từ django.db


from apps.dashboard.forms import CategoryForm, ProductUIForm
from apps.product.models import Category, Product


def trash_view(request):
    """Trang thùng rác"""
    deleted_products = Product.objects.filter(deleted_at__isnull=False)

    # Nếu Category chưa có deleted_at, truyền danh sách rỗng để không bị lỗi FieldError
    deleted_categories = Category.objects.filter(deleted_at__isnull=False)

    return render(
        request,
        "dashboard/products/trash/trash.html",
        {
            "products": deleted_products,
            "categories": deleted_categories,
        }
    )

# Alias chống lỗi nếu urls.py hoặc template cũ vẫn gọi product_trash_view
"""product_trash_view = trash_view"""


# ==============================================================================
# PRODUCT VIEWS
# ==============================================================================


def product_list_view(request):
    """Danh sách sản phẩm (Phân trang chuẩn 5/trang mặc định)"""
    products = Product.objects.filter(deleted_at__isnull=True)
    categories = Category.objects.filter(deleted_at__isnull=True)

    search = request.GET.get('search', '').strip()
    selected_category = request.GET.get('category', '').strip()
    status = request.GET.get('status', '').strip()
    sort = request.GET.get('sort', '').strip()

    # ĐỔI MẶC ĐỊNH THÀNH '5' (khớp với option đầu tiên ở HTML)
    per_page = request.GET.get('per_page', '5').strip()

    if search:
        products = products.filter(Q(sku__icontains=search) | Q(name__icontains=search))
    if selected_category:
        products = products.filter(category_id=selected_category)
    if status:
        products = products.filter(status=status)

    # Sắp xếp
    if sort == 'name_asc':
        products = products.order_by(Lower('name').asc())
    elif sort == 'name_desc':
        products = products.order_by(Lower('name').desc())
    else:
        sort_mapping = {
            'newest': '-created_at',
            'oldest': 'created_at',
            'price_asc': 'selling_price',
            'price_desc': '-selling_price',
        }
        products = products.order_by(sort_mapping.get(sort, '-created_at'))

    # XỬ LÝ SỐ LƯỢNG TRÊN 1 TRANG
    total_count = products.count()
    if per_page == 'all':
        items_per_page = total_count if total_count > 0 else 5
    else:
        try:
            items_per_page = int(per_page)
        except ValueError:
            items_per_page = 5

    paginator = Paginator(products, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "dashboard/products/products/list.html",
        {
            "products": page_obj,
            "categories": categories,
            "status_choices": Product.Status.choices,
            "search": search,
            "selected_category": selected_category,
            "status": status,
            "sort": sort,
            "per_page": per_page,
        }
    )

def product_create_view(request):
    """Thêm sản phẩm mới"""
    if request.method == "POST":
        form = ProductUIForm(request.POST, request.FILES) # Không truyền instance
        if form.is_valid():
            product = form.save(commit=False)
            if request.user.is_authenticated:
                product.created_by = request.user
            product.save()
            messages.success(request, "Thêm sản phẩm mới thành công.")
            return redirect("product-list")
        else:
            messages.error(request, "Không thể lưu! Vui lòng kiểm tra lại thông tin các ô bên dưới.")
    else:
        form = ProductUIForm() # Không truyền instance

    return render(
        request,
        "dashboard/products/create.html",
        {"form": form, "title": "Thêm sản phẩm mới"}
    )

def product_update_view(request, product_id):
    product = get_object_or_404(Product, pk=product_id, deleted_at__isnull=True)
    form = ProductUIForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == "POST":
        if form.is_valid():
            updated_product = form.save(commit=False)
            if request.user.is_authenticated:
                updated_product.updated_by = request.user
            updated_product.save()
            messages.success(request, "Cập nhật sản phẩm thành công.")
            return redirect("product-list")
        else:
            messages.error(request, "Không thể cập nhật! Giá bán không được nhỏ hơn hoặc bằng giá nhập.")

    return render(request, "dashboard/products/products/create.html", {"form": form, "title": "Sửa sản phẩm"})
@require_POST
def product_soft_delete_view(request, product_id):
    """Xóa mềm sản phẩm (Chuyển vào thùng rác)"""
    product = get_object_or_404(Product, pk=product_id, deleted_at__isnull=True)
    product.deleted_at = timezone.now()
    if request.user.is_authenticated:
        product.updated_by = request.user
    product.save(
        update_fields=["deleted_at", "updated_at", "updated_by"] if request.user.is_authenticated else ["deleted_at",
                                                                                                        "updated_at"])
    messages.success(request, f"Đã chuyển sản phẩm '{product.name}' vào thùng rác.")
    return redirect("product-list")


@require_POST
def product_restore_view(request, product_id):
    """Khôi phục sản phẩm"""
    product = get_object_or_404(Product, pk=product_id, deleted_at__isnull=False)
    product.deleted_at = None
    if request.user.is_authenticated:
        product.updated_by = request.user
    product.save(
        update_fields=["deleted_at", "updated_at", "updated_by"] if request.user.is_authenticated else ["deleted_at",
                                                                                                        "updated_at"])
    messages.success(request, f"Đã khôi phục sản phẩm '{product.name}'.")
    return redirect("trash")


@require_POST
def product_hard_delete_view(request, product_id):
    """Xóa vĩnh viễn sản phẩm khỏi CSDL (PRODUCT_TXN_GUARD — chặn nếu có Kho/Order/Invoice)."""
    product = get_object_or_404(Product, pk=product_id)
    product_name = product.name

    # PRODUCT_TXN_GUARD — chi tiết related_name: xem Product.has_transaction_history()
    if product.has_transaction_history():
        messages.error(
            request,
            f"KHÔNG THỂ XÓA HẲN! Sản phẩm '{product_name}' đã phát sinh lịch sử giao dịch "
            f"(Kho hàng, Đơn hàng hoặc Hóa đơn).",
        )
        return redirect("trash")
    try:
        product.delete()
        messages.success(request, f"Đã xóa vĩnh viễn sản phẩm '{product_name}'.")
    except (ProtectedError, IntegrityError):
        messages.error(
            request,
            f"KHÔNG THỂ XÓA HẲN! Sản phẩm '{product_name}' đang có ràng buộc dữ liệu không thể phá vỡ trong CSDL."
        )
    except Exception as e:
        messages.error(request, f"Không thể xóa sản phẩm do lỗi: {str(e)}")

    return redirect("trash")
# ==============================================================================
# CATEGORY VIEWS
# ==============================================================================
def category_list_view(request):
    """Danh sách danh mục (có đếm SP, Tìm kiếm, Lọc, Sắp xếp & Phân trang)"""
    categories = Category.objects.filter(deleted_at__isnull=True).annotate(
        active_product_count=Count('products', filter=Q(products__deleted_at__isnull=True))
    )

    # 1. Lấy tham số lọc từ URL
    search = request.GET.get('search', '').strip()
    has_products = request.GET.get('has_products', '').strip()
    sort = request.GET.get('sort', '').strip()
    per_page = request.GET.get('per_page', '5').strip()

    # 2. Tìm kiếm theo Tên hoặc Mô tả
    if search:
        categories = categories.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    # 3. Lọc theo trạng thái có/không có sản phẩm
    active_category_ids = Product.objects.filter(
        deleted_at__isnull=True,
        category__isnull=False
    ).values_list('category_id', flat=True).distinct()

    if has_products == 'yes':
        categories = categories.filter(id__in=active_category_ids)
    elif has_products == 'no':
        categories = categories.exclude(id__in=active_category_ids)

    # 4. Sắp xếp (Sort - Không phân biệt chữ hoa/thường với Lower)
    if sort == 'most_products':
        categories = categories.order_by('-active_product_count')
    elif sort == 'name_asc':
        categories = categories.order_by(Lower('name').asc())
    elif sort == 'name_desc':
        categories = categories.order_by(Lower('name').desc())
    else:
        sort_mapping = {
            'newest': '-created_at',
            'oldest': 'created_at',
        }
        order_by_field = sort_mapping.get(sort, 'name')
        categories = categories.order_by(order_by_field)

    # 5. XỬ LÝ PHÂN TRANG (PAGINATION)
    total_count = categories.count()
    if per_page == 'all':
        items_per_page = total_count if total_count > 0 else 5
    else:
        try:
            items_per_page = int(per_page)
        except ValueError:
            items_per_page = 5

    paginator = Paginator(categories, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "dashboard/categories/list.html",
        {
            "categories": page_obj,  # Truyền page_obj ra giao diện
            "search": search,
            "has_products": has_products,
            "sort": sort,
            "per_page": per_page,
        }
    )
def category_create_view(request):
    """Tạo danh mục mới"""
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        category = form.save(commit=False)
        if request.user.is_authenticated:
            category.created_by = request.user
            category.updated_by = request.user
        category.save()
        messages.success(request, "Đã thêm danh mục mới.")
        return redirect("category-list")
    return render(request, "dashboard/categories/form.html", {"form": form, "title": "Thêm danh mục"})


def category_update_view(request, category_id):
    """Cập nhật danh mục"""
    category = get_object_or_404(Category, pk=category_id)
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        updated_category = form.save(commit=False)
        if request.user.is_authenticated:
            updated_category.updated_by = request.user
        updated_category.save()
        messages.success(request, f"Đã cập nhật danh mục '{updated_category.name}'.")
        return redirect("category-list")
    return render(request, "dashboard/categories/form.html", {"form": form, "title": "Sửa danh mục"})


@require_POST
def category_soft_delete_view(request, category_id):
    """Xóa mềm danh mục (Chuyển vào thùng rác)"""
    category = get_object_or_404(Category, pk=category_id, deleted_at__isnull=True)

    # 1. Kiểm tra sản phẩm đang hoạt động thuộc danh mục
    has_active_products = Product.objects.filter(category=category, deleted_at__isnull=True).exists()

    if has_active_products:
        messages.error(
            request,
            f"Không thể xóa danh mục '{category.name}' vì vẫn còn sản phẩm thuộc danh mục này!"
        )
    else:
        # 2. BẮT BUỘC gán thời gian xóa mềm
        category.deleted_at = timezone.now()
        if request.user.is_authenticated:
            category.updated_by = request.user

        category.save(
            update_fields=["deleted_at", "updated_at", "updated_by"]
            if request.user.is_authenticated
            else ["deleted_at", "updated_at"]
        )
        messages.success(request, f"Đã chuyển danh mục '{category.name}' vào thùng rác.")

    return redirect("category-list")
@require_POST
def category_restore_view(request, category_id):
    """Khôi phục sản phẩm"""
    category = get_object_or_404(Category, pk=category_id, deleted_at__isnull=False)
    category.deleted_at = None
    if request.user.is_authenticated:
        category.updated_by = request.user
    category.save(
        update_fields=["deleted_at", "updated_at", "updated_by"] if request.user.is_authenticated else ["deleted_at",
                                                                                                        "updated_at"])
    messages.success(request, f"Đã khôi phục sản phẩm '{category.name}'.")
    return redirect("trash")


@require_POST
def category_hard_delete_view(request, category_id):
    """Xóa vĩnh viễn danh mục khỏi CSDL (Chặn khi vẫn còn sản phẩm)"""
    category = get_object_or_404(Category, pk=category_id)
    category_name = category.name

    # 1. KIỂM TRA CHỦ ĐỘNG: Không cho xóa nếu vẫn còn sản phẩm liên kết (kể cả SP trong thùng rác)
    if category.products.exists():
        messages.error(
            request,
            f"KHÔNG THỂ XÓA HẲN! Danh mục '{category_name}' vẫn còn liên kết với sản phẩm trong hệ thống."
        )
        return redirect("trash")

    # 2. BẢO VỆ CSDL
    try:
        category.delete()
        messages.success(request, f"Đã xóa vĩnh viễn danh mục '{category_name}'.")
    except (ProtectedError, IntegrityError):
        messages.error(
            request,
            f"KHÔNG THỂ XÓA HẲN! Danh mục '{category_name}' đang có ràng buộc dữ liệu trong CSDL."
        )
    except Exception as e:
        messages.error(request, f"Lỗi khi xóa danh mục: {str(e)}")

    return redirect("trash")