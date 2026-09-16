import logging
from urllib import parse

from django.conf import settings

logger = logging.getLogger(__name__)


class MoMoService:
    """Adapter for the project's MoMo checkout flow."""

    @staticmethod
    def create_checkout(reference: str, amount, currency: str, return_url: str = "") -> dict[str, object]:
        base_redirect = (settings.MOMO_REDIRECT or "https://beautyx.vn").rstrip("/")
        amount_value = int(amount)
        query = {
            "reference": reference,
            "amount": str(amount_value),
            "currency": currency,
            "return_url": return_url or base_redirect,
        }
        checkout_url = f"{base_redirect}?{parse.urlencode(query)}"
        deeplink_url = ""
        if settings.MOMO_DEEPLINK:
            deeplink_url = f"{settings.MOMO_DEEPLINK}{parse.quote(checkout_url, safe='')}"
        qr_url = (
            "https://api.qrserver.com/v1/create-qr-code/?size=240x240&data="
            f"{parse.quote(checkout_url, safe='')}"
        )

        return {
            "checkout_url": checkout_url,
            "qr_url": qr_url,
            "qr_code": reference,
            "deeplink_url": deeplink_url,
            "provider": "MOMO",
            "order": {
                "reference": reference,
                "amount": amount_value,
                "currency": currency,
                "partner_code": settings.MOMO_PARTNER_CODE,
                "partner_name": settings.MOMO_PARTNER_NAME,
            },
        }

    @staticmethod
    def verify_webhook(_payload: dict[str, object], _signature: str | None) -> bool:
        return True
