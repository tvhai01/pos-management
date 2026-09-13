from uuid import UUID

from django.db.models import QuerySet

from apps.payments.models import Payment, PaymentTransaction


class PaymentSelector:
    @staticmethod
    def get_all() -> QuerySet[Payment]:
        return Payment.objects.select_related("invoice", "invoice__customer").all()

    @staticmethod
    def get_by_id(payment_id: UUID | str) -> Payment | None:
        try:
            return Payment.objects.select_related("invoice").get(id=payment_id)
        except (Payment.DoesNotExist, ValueError, TypeError):
            return None

    @staticmethod
    def get_transactions(payment_id: UUID | str) -> QuerySet[PaymentTransaction]:
        return PaymentTransaction.objects.filter(payment_id=payment_id).order_by("created_at")