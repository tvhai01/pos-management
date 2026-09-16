"""Thin adapters over the Gemini and Groq HTTP APIs.

Follows the same shape as `apps/payments/sepay.py`: stdlib `urllib`, a
short timeout, and network/parse errors turned into one exception type
instead of leaking `urllib`/`json` internals to callers. Secrets never
appear in logs or exceptions.
"""

import json
import logging
from urllib import error, request

from django.conf import settings

logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    """Raised when a provider is not configured or a call fails/times out."""


def _post_json(url: str, payload: dict, headers: dict[str, str]) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(  # noqa: S310 - url is settings-controlled, not user input
        url,
        data=body,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with request.urlopen(  # noqa: S310 - same trusted, settings-controlled url
            req, timeout=settings.AI_INSIGHT_TIMEOUT
        ) as response:
            return json.loads(response.read().decode())
    except (error.URLError, TimeoutError, ValueError, UnicodeDecodeError) as exc:
        raise AIProviderError(str(exc)) from exc


class GeminiProvider:
    """Google Generative Language API — `generateContent`, JSON-mode output."""

    name = "gemini"

    @staticmethod
    def generate(prompt: str) -> str:
        if not settings.GEMINI_API_KEY:
            raise AIProviderError("gemini_not_configured")

        url = (
            f"{settings.GEMINI_API_URL.rstrip('/')}/{settings.GEMINI_MODEL}"
            f":generateContent?key={settings.GEMINI_API_KEY}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }
        try:
            data = _post_json(url, payload, headers={})
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except AIProviderError:
            raise
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning("Gemini returned an unexpected response shape: %s", exc)
            raise AIProviderError("gemini_unexpected_response") from exc


class GroqProvider:
    """Groq's OpenAI-compatible `chat/completions` endpoint, JSON-mode output."""

    name = "groq"

    @staticmethod
    def generate(prompt: str) -> str:
        if not settings.GROQ_API_KEY:
            raise AIProviderError("groq_not_configured")

        payload = {
            "model": settings.GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
        try:
            data = _post_json(settings.GROQ_API_URL, payload, headers=headers)
            return data["choices"][0]["message"]["content"]
        except AIProviderError:
            raise
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning("Groq returned an unexpected response shape: %s", exc)
            raise AIProviderError("groq_unexpected_response") from exc
