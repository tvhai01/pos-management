from django.contrib import admin
from django.urls import path
from apps.dashboard import views
from django.conf.urls.static import static
from django.conf import settings

app_name = "products"
urlpatterns = [
    #path('admin/', admin.site.urls),

    # Định nghĩa cả 2 tên name='trash' và name='product-trash' để khớp với template
    path('trash/', views.trash_view, name='trash'),
    path('products/trash/', views.trash_view, name='product-trash'),

    # Product URLs
    path('products/', views.product_list_view, name='product-list'),
    path('products/create/', views.product_create_view, name='product-create'),
    path('products/<uuid:product_id>/edit/', views.product_update_view, name='product-edit'),
    path('products/<uuid:product_id>/delete/', views.product_soft_delete_view, name='product-delete'),
    path('products/<uuid:product_id>/restore/', views.product_restore_view, name='product-restore'),
    path('products/<uuid:product_id>/hard-delete/', views.product_hard_delete_view, name='product-hard-delete'),

    # Category URLs
    path('categories/', views.category_list_view, name='category-list'),
    path('categories/create/', views.category_create_view, name='category-create'),
    path('categories/<uuid:category_id>/edit/', views.category_update_view, name='category-edit'),
    path('categories/<uuid:category_id>/delete/', views.category_soft_delete_view, name='category-delete'),
    # (Hoặc <int:category_id> nếu ID của danh mục dùng số tự tăng)
    path('categories/<uuid:category_id>/restore/', views.category_restore_view, name='category-restore'),
    path('categories/<uuid:category_id>/hard-delete/', views.category_hard_delete_view, name='category-hard-delete'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)