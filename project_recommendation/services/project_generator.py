from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from ai.config import is_configured
from ai.provider import ensure_configured, get_chat_model

from project_recommendation.exceptions import (
    ProjectRecommendationConfigurationError,
    ProjectRecommendationValidationError,
)
from project_recommendation.prompts.project_prompt import (
    build_project_prompt,
    format_prompt_inputs,
)
from project_recommendation.schemas.project_output import ProjectRecommendationPayload
from utils.token_usage import extract_token_usage

logger = logging.getLogger(__name__)

_MAX_GENERATION_ATTEMPTS = 2


class ProjectGenerator:
    """Single LLM invocation: career info -> structured project recommendations."""

    @classmethod
    def generate(
        cls,
        *,
        career_name: str,
        match_percentage: int,
        required_skills: str,
        career_insight: str,
    ) -> tuple[ProjectRecommendationPayload, int]:
        if not is_configured():
            raise ProjectRecommendationConfigurationError(
                "AI project recommendation is temporarily unavailable"
            )
        ensure_configured()

        prompt = build_project_prompt()
        llm = get_chat_model()
        last_error: ProjectRecommendationValidationError | None = None
        validation_feedback = "None"

        for attempt in range(_MAX_GENERATION_ATTEMPTS):
            try:
                inputs = format_prompt_inputs(
                    career_name=career_name,
                    match_percentage=match_percentage,
                    required_skills=required_skills,
                    career_insight=career_insight,
                    validation_feedback=validation_feedback,
                )
                return cls._invoke_once(
                    prompt=prompt,
                    inputs=inputs,
                    llm=llm,
                )
            except ProjectRecommendationValidationError as exc:
                last_error = exc
                validation_feedback = _clip_feedback(exc.details)
                if (
                    not _is_retryable_generation_error(exc)
                    or attempt == _MAX_GENERATION_ATTEMPTS - 1
                ):
                    raise
                logger.warning(
                    "Retrying project generation after %s (attempt %s/%s)",
                    exc.error,
                    attempt + 2,
                    _MAX_GENERATION_ATTEMPTS,
                )

        raise last_error or ProjectRecommendationValidationError(
            "Project generation failed",
            error="Validation failed",
            details="Project generation failed after retries",
        )

    @classmethod
    def _invoke_once(
        cls,
        *,
        prompt,
        inputs: dict[str, str],
        llm,
    ) -> tuple[ProjectRecommendationPayload, int]:
        try:
            chain = prompt | llm
            result = chain.invoke(inputs)
            token_usage = extract_token_usage(result)
            raw_text = _extract_text_content(result)
            if not raw_text or not raw_text.strip():
                raise ProjectRecommendationValidationError(
                    "Empty response from AI",
                    error="Generation failed",
                    details="AI returned an empty response",
                )

            parsed = json.loads(raw_text)
            if not isinstance(parsed, dict):
                raise ProjectRecommendationValidationError(
                    "Response is not a valid JSON object",
                    error="Generation failed",
                    details="AI response root must be a JSON object",
                )

            payload = _parse_ai_payload(parsed)
            return payload, token_usage
        except json.JSONDecodeError as exc:
            logger.warning("Project generation JSON parse failed: %s", exc)
            raise ProjectRecommendationValidationError(
                "Unable to generate project ideas. Please try again.",
                error="Generation failed",
                details="AI response could not be parsed as valid JSON",
            ) from exc
        except (ValidationError, ValueError) as exc:
            logger.warning("Project generation validation failed: %s", exc)
            raise ProjectRecommendationValidationError(
                str(exc),
                error="Validation failed",
                details=str(exc),
            ) from exc
        except ProjectRecommendationValidationError:
            raise
        except Exception as exc:
            logger.exception("LLM project generation failed")
            raise ProjectRecommendationValidationError(
                _format_llm_error(exc),
                error="LLM request failed",
                details=_format_llm_error(exc),
            ) from exc


def _parse_ai_payload(payload: Any) -> ProjectRecommendationPayload:
    if isinstance(payload, ProjectRecommendationPayload):
        return payload
    if isinstance(payload, dict):
        return ProjectRecommendationPayload.model_validate(_normalize_payload(payload))
    raise ValueError("AI response must be a JSON object")


def _normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "project_list": "projects",
        "projectList": "projects",
        "suggestions": "projects",
        "items": "projects",
    }
    normalized: dict[str, Any] = {}
    for key, value in data.items():
        target = aliases.get(key, key)
        if target in normalized and normalized[target] not in (None, "", []):
            continue
        normalized[target] = value
    return normalized


def _extract_text_content(result: Any) -> str:
    if isinstance(result, str):
        return result

    content = getattr(result, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif hasattr(block, "text"):
                parts.append(str(block.text))
        return "".join(parts)
    return str(result)


def _format_llm_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()
    if "insufficient_quota" in lowered or "quota" in lowered or "429" in lowered:
        return "Project generation is busy right now. Please try again shortly."
    return "Unable to generate project ideas right now. Please try again."


def _is_retryable_generation_error(exc: ProjectRecommendationValidationError) -> bool:
    return exc.error in ("Generation failed", "Validation failed")


def _clip_feedback(message: str) -> str:
    text = " ".join(message.split())
    if len(text) <= 240:
        return text
    return text[:237].rstrip() + "..."
