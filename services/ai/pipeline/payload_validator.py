from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from services.ai.exceptions import AIGenerationError
from services.ai.pipeline.ai_input_normalizer import normalize_raw_payload
from services.ai.schemas.recommendation_output import AIRecommendationPayload

logger = logging.getLogger(__name__)


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


def parse_ai_payload_lenient(raw: Any) -> AIRecommendationPayload | None:
    """Best-effort parse; returns None if validation still fails."""
    try:
        return parse_ai_payload(raw)
    except ValidationError as exc:
        logger.warning("AI payload validation failed after normalization: %s", exc)
        return None
    except (TypeError, ValueError) as exc:
        logger.warning("AI payload could not be coerced: %s", exc)
        return None


def require_ai_payload(raw: Any) -> AIRecommendationPayload:
    payload = parse_ai_payload_lenient(raw)
    if payload is None:
        raise AIGenerationError(
            "AI response could not be validated after normalization."
        )
    return payload
