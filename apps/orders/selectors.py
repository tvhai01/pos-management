from uuid import UUID

from django.db.models import QuerySet

from apps.orders.models import Order


class OrderSelector:
    @staticmethod
    def get_all() -> QuerySet[Order]:
        return Order.objects.select_related("customer").prefetch_related("items").all()

    @staticmethod
    def get_by_id(order_id: UUID | str) -> Order | None:
        try:
            return Order.objects.select_related("customer").prefetch_related("items__product").get(id=order_id)
        except (Order.DoesNotExist, ValueError, TypeError):
            return None