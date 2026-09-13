from decimal import Decimal

from apps.payments.constants import PaymentStatus, Provider
from apps.payments.models import Payment, PaymentTransaction


class PaymentReconciliationService:
    """Report provider mismatches without mutating financial records."""

    @staticmethod
    def compare_payment(payment: Payment, provider_rows: list[dict[str, object]]) -> list[dict[str, object]]:
        local_transactions = PaymentTransaction.objects.filter(payment=payment)
        local_ids = set(local_transactions.exclude(provider_transaction_id=None).values_list("provider_transaction_id", flat=True))
        mismatches: list[dict[str, object]] = []
        for row in provider_rows:
            provider_id = str(row.get("transaction_id") or row.get("id") or "")
            provider_amount = Decimal(str(row.get("amount", "0")))
            if provider_id not in local_ids:
                mismatches.append({"type": "provider_transaction_missing_locally", "provider_transaction_id": provider_id})
            if provider_amount != payment.amount:
                mismatches.append({"type": "amount_mismatch", "provider_transaction_id": provider_id, "local_amount": payment.amount, "provider_amount": provider_amount})
        if payment.status == PaymentStatus.SUCCESS and not local_transactions.filter(provider=Provider.SEPAY, status=PaymentStatus.SUCCESS).exists():
            mismatches.append({"type": "local_success_without_provider_success", "payment_id": str(payment.id)})
        return mismatches