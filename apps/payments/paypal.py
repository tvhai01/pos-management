from __future__ import annotations

import base64
import json
from decimal import Decimal, ROUND_HALF_UP
from urllib import error, request
from urllib.parse import urlencode

from django.conf import settings


class PayPalService:
    """Adapter for the PayPal REST checkout flow used by the POS app."""

    @staticmethod
    def _provider_amount(amount, currency: str) -> tuple[Decimal, str]:
        provider_currency = str(getattr(settings, "PAYPAL_CURRENCY", "USD")).upper()
        source_currency = str(currency or provider_currency).upper()
        source_amount = Decimal(str(amount))
        if source_currency == provider_currency:
            return source_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), provider_currency
        if source_currency == "VND" and provider_currency == "USD":
            rate = Decimal(str(getattr(settings, "PAYPAL_VND_TO_USD_RATE", "25000")))
            if rate <= 0:
                raise ValueError("PAYPAL_VND_TO_USD_RATE must be greater than zero.")
            return (source_amount / rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), provider_currency
        raise ValueError(f"PayPal does not support currency conversion from {source_currency} to {provider_currency}.")

    @staticmethod
    def _request_json(url: str, *, method: str = "GET", body: dict | None = None, auth: tuple[str, str] | None = None, headers: dict | None = None) -> dict:
        payload = None
        req_headers = {"Accept": "application/json"}
        if headers:
            req_headers.update(headers)
        if body is not None:
            if req_headers.get("Content-Type") == "application/x-www-form-urlencoded":
                payload = urlencode(body).encode("utf-8")
            else:
                payload = json.dumps(body).encode("utf-8")
                req_headers.setdefault("Content-Type", "application/json")
        if auth is not None:
            creds = base64.b64encode(f"{auth[0]}:{auth[1]}".encode("utf-8")).decode("ascii")
            req_headers.setdefault("Authorization", f"Basic {creds}")
        req = request.Request(url, data=payload, headers=req_headers, method=method)
        try:
            with request.urlopen(req, timeout=30) as response:
                content = response.read().decode("utf-8")
                return json.loads(content) if content else {}
        except error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="ignore")
            try:
                detail = json.loads(body_text)
            except json.JSONDecodeError:
                detail = {"error": body_text}
            raise ValueError(f"PayPal API error: {detail}") from exc

    @staticmethod
    def get_access_token() -> str:
        if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_SECRET:
            return "local-paypal-dev-token"
        token_url = f"{settings.PAYPAL_BASE_URL}/v1/oauth2/token"
        data = {"grant_type": "client_credentials"}
        response = PayPalService._request_json(
            token_url,
            method="POST",
            body=data,
            auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        access_token = response.get("access_token")
        if not access_token:
            raise ValueError("PayPal access token not returned by provider.")
        return str(access_token)

    @staticmethod
    def create_checkout(reference: str, amount, currency: str, return_url: str = "", cancel_url: str = "") -> dict[str, object]:
        provider_amount, provider_currency = PayPalService._provider_amount(amount, currency)
        if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_SECRET:
            checkout_url = (return_url or settings.PAYPAL_REDIRECT_URL or "https://pos.dyca.vn/payment/paypal/success")
            if "?" in checkout_url:
                checkout_url = f"{checkout_url}&paypal_order_id={reference}"
            else:
                checkout_url = f"{checkout_url}?paypal_order_id={reference}"
            return {
                "checkout_url": checkout_url,
                "qr_url": "",
                "qr_code": reference,
                "deeplink_url": "",
                "provider": "PAYPAL",
                "order": {
                    "reference": reference,
                    "paypal_order_id": reference,
                    "amount": float(provider_amount),
                    "currency": provider_currency,
                    "original_amount": float(amount),
                    "original_currency": currency,
                    "return_url": return_url or settings.PAYPAL_REDIRECT_URL,
                    "cancel_url": cancel_url or settings.PAYPAL_CANCEL_URL,
                },
            }
        access_token = PayPalService.get_access_token()
        order_url = f"{settings.PAYPAL_BASE_URL}/v2/checkout/orders"
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": reference,
                    "amount": {
                        "currency_code": provider_currency,
                        "value": f"{provider_amount:.2f}",
                    },
                }
            ],
            "application_context": {
                "return_url": return_url or settings.PAYPAL_REDIRECT_URL,
                "cancel_url": cancel_url or settings.PAYPAL_CANCEL_URL,
                "brand_name": "POS Management",
                "user_action": "PAY_NOW",
            },
        }
        response = PayPalService._request_json(
            order_url,
            method="POST",
            body=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        order_id = response.get("id") or reference
        approve_url = ""
        for link in response.get("links", []):
            if link.get("rel") == "approve":
                approve_url = link.get("href", "")
                break
        if not approve_url:
            raise ValueError("PayPal approval link was not returned by provider.")
        return {
            "checkout_url": approve_url,
            "qr_url": "",
            "qr_code": order_id,
            "deeplink_url": "",
            "provider": "PAYPAL",
            "order": {
                "reference": reference,
                "paypal_order_id": order_id,
                "amount": float(provider_amount),
                "currency": provider_currency,
                "original_amount": float(amount),
                "original_currency": currency,
                "return_url": return_url or settings.PAYPAL_REDIRECT_URL,
                "cancel_url": cancel_url or settings.PAYPAL_CANCEL_URL,
            },
        }

    @staticmethod
    def capture_order(order_id: str) -> dict:
        if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_SECRET:
            return {"id": order_id, "status": "COMPLETED"}
        access_token = PayPalService.get_access_token()
        capture_url = f"{settings.PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture"
        response = PayPalService._request_json(
            capture_url,
            method="POST",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return response

    @staticmethod
    def verify_webhook(_payload: dict[str, object], _signature: str | None) -> bool:
        return True
