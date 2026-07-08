"""Narrative synthesis via the DeepSeek API (OpenAI-compatible chat
completions). Falls back to a deterministic analyst note composed from the
numbers when no API key is configured, in tests, or on any failure."""

import json
import logging
import os

import httpx

from config import get_settings
from models import Fund, FundMetrics

logger = logging.getLogger("diafanis.deepseek")

SYSTEM_PROMPT = (
    "You are an independent private-markets analyst writing for an LP who "
    "holds or is considering buying/selling a stake in this fund. You are "
    "given model-estimated metrics: TVPI (net multiple), DPI (realized), "
    "RVPI (unrealized), net IRR, and PME alpha (cash-weighted excess return "
    "vs a public benchmark of comparable listed companies; positive = beat "
    "the benchmark). Confidence indicates whether the model was calibrated "
    "to a public reported mark. Write a plain-English 3-4 sentence read on "
    "what these estimates imply for a holder or secondary buyer — direction, "
    "how much is still unrealized, and how it compares to just holding the "
    "public benchmark. Do not invent facts beyond the inputs. Respond with "
    'strict JSON: {"narrative": "..."}. No markdown.'
)


def _is_test_runtime() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def _deterministic_narrative(fund: Fund, metrics: FundMetrics) -> str:
    parts: list[str] = []
    direction = (
        "ahead of" if (metrics.pme_alpha or 0) > 0.02
        else "behind" if (metrics.pme_alpha or 0) < -0.02
        else "roughly in line with"
    )
    parts.append(
        f"Our model estimates {fund.name} (vintage {fund.vintage_year}) at "
        f"{metrics.est_tvpi:.2f}x net TVPI, with {metrics.est_dpi:.2f}x already "
        f"distributed and {metrics.est_rvpi:.2f}x still unrealized."
    )
    if metrics.est_net_irr is not None:
        parts.append(f"That pencils to an estimated net IRR of {metrics.est_net_irr:.1%}.")
    if metrics.pme_alpha is not None:
        parts.append(
            f"On a cash-weighted basis the fund is {direction} its public benchmark "
            f"(PME alpha {metrics.pme_alpha:+.1%})."
        )
    if metrics.confidence == "high" and fund.reported_source:
        parts.append(
            f"The estimate is calibrated to a public mark ({fund.reported_source}) "
            "and rolled forward with benchmark returns since."
        )
    elif metrics.confidence == "low":
        parts.append(
            "No public mark is available for this fund, so this is a pacing-model "
            "estimate only — treat it as directional."
        )
    return " ".join(parts)


def _parse_json_response(text: str) -> str | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        payload = json.loads(cleaned)
        return payload.get("narrative")
    except (json.JSONDecodeError, AttributeError):
        return None


def generate_fund_narrative(fund: Fund, metrics: FundMetrics) -> str:
    settings = get_settings()
    if _is_test_runtime() or not settings.deepseek_api_key:
        return _deterministic_narrative(fund, metrics)

    user_prompt = json.dumps(
        {
            "fund_name": fund.name,
            "provider": fund.provider.name if fund.provider else None,
            "vintage_year": fund.vintage_year,
            "asset_class": fund.asset_class,
            "status": fund.status,
            "est_tvpi": metrics.est_tvpi,
            "est_dpi": metrics.est_dpi,
            "est_rvpi": metrics.est_rvpi,
            "est_net_irr": metrics.est_net_irr,
            "pme_alpha": metrics.pme_alpha,
            "confidence": metrics.confidence,
            "reported_source": fund.reported_source,
        }
    )

    try:
        response = httpx.post(
            f"{settings.deepseek_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            json={
                "model": settings.deepseek_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "max_tokens": 400,
            },
            timeout=15,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        narrative = _parse_json_response(content)
        if narrative:
            return narrative
        logger.warning("DeepSeek response missing narrative field")
    except Exception:
        logger.warning("DeepSeek call failed", exc_info=True)

    return _deterministic_narrative(fund, metrics)
