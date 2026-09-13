import hashlib
import hmac
import json
import logging
from urllib import error, request

from django.conf import settings

logger = logging.getLogger(__name__)


class SePayService:
    """Small provider adapter; secrets never leave this module."""

    @staticmethod
    def signature(fields: dict[str, object]) -> str:
        payload = "&".join(f"{key}={value}" for key, value in fields.items())
        return hmac.new(settings.SEPAY_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def verify_webhook(payload: dict[str, object], supplied_signature: str | None) -> bool:
        if not settings.SEPAY_SECRET_KEY or not supplied_signature:
            return False
        received = dict(payload)
        received.pop("signature", None)
        expected = SePayService.signature(received)
        return hmac.compare_digest(expected, supplied_signature)

    @staticmethod
    def create_checkout(reference: str, amount, currency: str, return_url: str = "") -> dict[str, object]:
        fields = {"merchant_id": settings.SEPAY_MERCHANT_ID, "order_invoice_number": reference, "amount": amount, "currency": currency, "return_url": return_url}
        return {"checkout_url": settings.SEPAY_CHECKOUT_URL, "fields": {**fields, "signature": SePayService.signature(fields)}}

    @staticmethod
    def _get(path: str) -> dict[str, object]:
        url = f"{settings.SEPAY_API_URL.rstrip('/')}/{path.lstrip('/')}"
        try:
            with request.urlopen(request.Request(url, headers={"Accept": "application/json"}), timeout=10) as response:
                return json.loads(response.read().decode())
        except (error.URLError, TimeoutError, ValueError) as exc:
            logger.warning("SePay API unavailable: path=%s error=%s", path, exc)
            return {"error": "provider_unavailable"}

    @staticmethod
    def get_order(reference: str) -> dict[str, object]:
        return SePayService._get(f"v1/orders/{reference}")

    @staticmethod
    def get_transaction(transaction_id: str) -> dict[str, object]:
        return SePayService._get(f"v1/transactions/{transaction_id}")

    @staticmethod
    def list_transactions() -> dict[str, object]:
        return SePayService._get("v1/transactions")

    @staticmethod
    def cancel_order(reference: str) -> dict[str, object]:
        return SePayService._get(f"v1/orders/{reference}/cancel")