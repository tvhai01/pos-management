import hashlib
import hmac
import json
import logging
from urllib import error, parse, request

from django.conf import settings

logger = logging.getLogger(__name__)


class SePayService:
    """Adapter for SePay checkout callbacks and the v2 transactions API."""

    @staticmethod
    def signature(fields: dict[str, object]) -> str:
        payload = "&".join(f"{key}={value}" for key, value in fields.items())
        return hmac.new(
            settings.SEPAY_WEBHOOK_SECRET.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

    @staticmethod
    def verify_webhook(payload: dict[str, object], supplied_signature: str | None) -> bool:
        if not settings.SEPAY_WEBHOOK_SECRET or not supplied_signature:
            return False
        received = dict(payload)
        received.pop("signature", None)
        expected = SePayService.signature(received)
        return hmac.compare_digest(expected, supplied_signature)

    @staticmethod
    def _headers() -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if settings.SEPAY_KEY:
            headers["Authorization"] = f"Bearer {settings.SEPAY_KEY}"
        return headers

    @staticmethod
    def _request(method: str, path: str, *, query=None, payload=None) -> dict[str, object]:
        url = f"{settings.SEPAY_API_URL.rstrip('/')}/{path.lstrip('/')}"
        if query:
            url = f"{url}?{parse.urlencode(query)}"
        if not settings.SEPAY_KEY:
            raise ValueError("SEPAY_KEY is not configured.")
        headers = SePayService._headers()
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload, default=str).encode()
        try:
            with request.urlopen(
                request.Request(url, data=data, headers=headers, method=method), timeout=10
            ) as response:
                body = json.loads(response.read().decode())
                if not isinstance(body, dict):
                    raise ValueError("Invalid SePay API response.")
                return body
        except error.HTTPError as exc:
            try:
                body = json.loads(exc.read().decode())
            except (UnicodeDecodeError, ValueError):
                body = {}
            error_code = body.get("error_code", "provider_error")
            detail = body.get("message") or body.get("error") or body.get("errors")
            suffix = f" - {detail}" if detail else ""
            raise ValueError(f"SePay API error: {error_code}{suffix}") from exc
        except (error.URLError, TimeoutError, ValueError) as exc:
            logger.warning("SePay API unavailable: path=%s error=%s", path, exc)
            raise ValueError("SePay API is unavailable.") from exc

    @staticmethod
    def _get(path: str, *, query=None) -> dict[str, object]:
        return SePayService._request("GET", path, query=query)

    @staticmethod
    def list_bank_accounts() -> dict[str, object]:
        return SePayService._get("bank-accounts")

    @staticmethod
    def create_order(
        bank_account_uuid: str,
        reference: str,
        amount,
        currency: str,
        return_url: str = "",
    ) -> dict[str, object]:
        return SePayService._request(
            "POST",
            f"bank-accounts/{bank_account_uuid}/orders",
            payload={
                "order_invoice_number": reference,
                "amount": int(amount),
            },
        )

    @staticmethod
    def create_checkout(reference: str, amount, currency: str, return_url: str = "") -> dict[str, object]:
        bank_id = settings.VIETQR_BANK_ID.strip()
        account_number = settings.VIETQR_ACCOUNT_NUMBER.strip()
        account_name = settings.VIETQR_ACCOUNT_NAME.strip()
        if not bank_id or not account_number:
            raise ValueError("VIETQR_BANK_ID and VIETQR_ACCOUNT_NUMBER are required.")
        qr_query = parse.urlencode(
            {
                "amount": int(amount),
                "addInfo": reference,
                "accountName": account_name,
            }
        )
        return {
            "checkout_url": "",
            "qr_url": (
                f"https://img.vietqr.io/image/{bank_id}-{account_number}-compact2.png?"
                f"{qr_query}"
            ),
            "qr_code": reference,
            "order": {
                "reference": reference,
                "amount": int(amount),
                "currency": currency,
                "bank_id": bank_id,
                "account_number": account_number,
            },
        }

    @staticmethod
    def get_order(reference: str) -> dict[str, object]:
        raise ValueError("Use get_transaction with a SePay UUID.")

    @staticmethod
    def get_transaction(transaction_id: str) -> dict[str, object]:
        return SePayService._get(f"transactions/{transaction_id}")

    @staticmethod
    def list_transactions(page: int = 1, per_page: int = 20, since_id: str = "", **filters) -> dict[str, object]:
        query = {"page": page, "per_page": min(per_page, 100)}
        if since_id:
            query["since_id"] = since_id
        query.update({key: value for key, value in filters.items() if value not in (None, "")})
        return SePayService._get("transactions", query=query)

    @staticmethod
    def cancel_order(reference: str) -> dict[str, object]:
        logger.info("SePay v2 does not provide order cancellation: reference=%s", reference)
        return {"error": "unsupported_operation"}