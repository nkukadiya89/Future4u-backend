from __future__ import annotations

from typing import Any

from recommendation.pipeline.ai_input_normalizer import normalize_raw_payload
from recommendation.schemas.recommendation_output import AIRecommendationPayload


def _raw_to_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, AIRecommendationPayload):
        return raw.model_dump()
    if hasattr(raw, "model_dump"):
        return raw.model_dump()
    if isinstance(raw, dict):
        return raw
    return dict(raw)


def parse_ai_payload(raw: Any) -> AIRecommendationPayload:
    """Normalize then validate Groq output only (no template/DB field injection)."""
    normalized = normalize_raw_payload(_raw_to_dict(raw))
    return AIRecommendationPayload.model_validate(normalized)
