from uuid import UUID

from django.db.models import QuerySet

from apps.invoices.models import Invoice


class InvoiceSelector:
    @staticmethod
    def get_all() -> QuerySet[Invoice]:
        return Invoice.objects.select_related("customer").all()

    @staticmethod
    def get_by_id(invoice_id: UUID | str) -> Invoice | None:
        try:
            return Invoice.objects.select_related("customer").get(id=invoice_id)
        except (Invoice.DoesNotExist, ValueError, TypeError):
            return None