from django.urls import path

from apps.orders.views import OrderDetailView, OrderListCreateView

app_name = "orders"
urlpatterns = [
    path("orders/", OrderListCreateView.as_view(), name="order-list-create"),
    path("orders/<uuid:order_id>/", OrderDetailView.as_view(), name="order-detail"),
]