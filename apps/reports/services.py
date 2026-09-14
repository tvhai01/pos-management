"""AI Insight orchestration for Report — the one Service in this app.

Report has no writes to orchestrate (see `views.py`'s docstring), but
generating an insight *is* business logic: call an external provider with a
fallback chain, validate its shape, and cache the result. That belongs here,
not in a view or selector (coding-convention.md §3.1).

Fallback chain: Gemini -> Groq -> RuleBasedInsightGenerator. The last step
never raises, so `generate()` always returns a usable result even with no
provider configured or reachable.
"""

import hashlib
import json
import logging
from typing import Any

from django.conf import settings
from django.core.cache import cache

from apps.reports.ai.prompts import build_prompt
from apps.reports.ai.providers import AIProviderError, GeminiProvider, GroqProvider
from apps.reports.constants import AIInsightSource
from apps.reports.insights import RuleBasedInsightGenerator

logger = logging.getLogger(__name__)

_PROVIDERS = (
    (AIInsightSource.GEMINI, GeminiProvider),
    (AIInsightSource.GROQ, GroqProvider),
)


def _cache_key(report_type: str, params: dict[str, Any]) -> str:
    normalized = json.dumps(params, sort_keys=True, default=str)
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return f"report:insight:{report_type}:{digest}"


def _parse_provider_output(raw: str) -> dict[str, Any]:
    parsed = json.loads(raw)
    summary = parsed["summary"]
    recommendations = parsed["recommendations"]
    if not isinstance(summary, str) or not isinstance(recommendations, list):
        raise ValueError("unexpected insight shape")
    return {
        "summary": summary,
        "recommendations": [str(item) for item in recommendations],
    }


class ReportInsightService:
    """Generate a `{summary, recommendations, source}` insight for one report."""

    @staticmethod
    def generate(
        report_type: str, data: Any, cache_key_params: dict[str, Any]
    ) -> dict[str, Any]:
        key = _cache_key(report_type, cache_key_params)
        cached = cache.get(key)
        if cached is not None:
            return cached

        result = ReportInsightService._call_providers(report_type, data)
        cache.set(key, result, settings.AI_INSIGHT_CACHE_TTL)
        return result

    @staticmethod
    def _call_providers(report_type: str, data: Any) -> dict[str, Any]:
        prompt = build_prompt(report_type, data)
        for source, provider in _PROVIDERS:
            try:
                raw = provider.generate(prompt)
                return {**_parse_provider_output(raw), "source": source}
            except AIProviderError as exc:
                logger.info(
                    "%s unavailable for %s insight: %s", provider.name, report_type, exc
                )
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                logger.warning(
                    "%s returned an unparsable insight for %s: %s",
                    provider.name,
                    report_type,
                    exc,
                )

        return {
            **RuleBasedInsightGenerator.generate(report_type, data),
            "source": AIInsightSource.RULE_BASED,
        }
