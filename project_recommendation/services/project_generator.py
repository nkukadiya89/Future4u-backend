from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from django.conf import settings

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

_MAX_GENERATION_ATTEMPTS = 1


class ProjectGenerator:
    """Single LLM invocation: domain/career input -> structured projects."""

    @classmethod
    def generate(
        cls,
        *,
        domain: str,
        domain_category: str,
        career_name: str,
        overview: str = "",
    ) -> tuple[ProjectRecommendationPayload, int]:
        if not is_configured():
            raise ProjectRecommendationConfigurationError(
                "AI project recommendation is temporarily unavailable"
            )
        ensure_configured()

        prompt = build_project_prompt()
        llm = get_chat_model(max_tokens=900)
        last_error: ProjectRecommendationValidationError | None = None
        validation_feedback = "None"

        for attempt in range(_MAX_GENERATION_ATTEMPTS):
            try:
                inputs = format_prompt_inputs(
                    domain=domain,
                    domain_category=domain_category,
                    career_name=career_name,
                    validation_feedback=validation_feedback,
                    overview=overview,
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
            # If AI returns a list of projects directly, wrap it
            if isinstance(parsed, list):
                parsed = {"projects": parsed}
            elif not isinstance(parsed, dict):
                raise ProjectRecommendationValidationError(
                    "Response is not a valid JSON object",
                    error="Generation failed",
                    details="AI response root must be a JSON object",
                )

            payload = _normalize_payload(parsed)
            return payload, token_usage
        except json.JSONDecodeError as exc:
            logger.warning("Project generation JSON parse failed: %s", exc)
            raise ProjectRecommendationValidationError(
                "Unable to generate project recommendations. Please try again.",
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


def _extract_text_content(result: Any) -> str:
    if isinstance(result, str):
        return result
    content = getattr(result, "content", None)
    if isinstance(content, str):
        # Strip markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            # Remove opening fence (```json, ```python, or just ```)
            first_newline = content.find("\n")
            if first_newline != -1:
                content = content[first_newline + 1 :]
            # Remove closing fence
            if content.endswith("```"):
                content = content[:-3].rstrip()
        return content
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
    return "Unable to generate project recommendations right now. Please try again."


def _is_retryable_generation_error(exc: ProjectRecommendationValidationError) -> bool:
    return exc.error in ("Generation failed", "Validation failed")


def _clip_feedback(message: str) -> str:
    text = " ".join(message.split())
    if len(text) <= 240:
        return text
    return text[:237].rstrip() + "..."


def _normalize_payload(raw: dict[str, Any]) -> ProjectRecommendationPayload:
    """Normalize AI response keys and validate via Pydantic."""
    if "projects" not in raw:
        # Check for numbered keys like project1, project2, project3
        numbered_keys = [k for k in raw if k.startswith("project") and k[7:].isdigit()]
        if numbered_keys:
            sorted_keys = sorted(numbered_keys, key=lambda k: int(k[7:]))
            raw["projects"] = [raw.pop(k) for k in sorted_keys]
        else:
            for alt_key in ("recommendations", "project_list", "portfolio_projects"):
                if alt_key in raw and isinstance(raw[alt_key], list):
                    raw["projects"] = raw.pop(alt_key)
                    break

    projects = raw.get("projects", [])
    if isinstance(projects, list):
        for item in projects:
            _rename_key(item, "recommendation_name", "project_name")
            _rename_key(item, "name", "project_name")
            _rename_key(item, "title", "project_name")
            _rename_key(item, "description", "short_description")
            _rename_key(item, "skills", "skills_gained")
            _rename_key(item, "key_skills", "skills_gained")
            _rename_key(item, "key_outcomes", "deliverables")
            _rename_key(item, "features", "deliverables")
            _rename_key(item, "deliverable", "deliverables")
            _rename_key(item, "duration", "estimated_duration")
            _rename_key(item, "project_duration", "estimated_duration")
            _rename_key(item, "portfolio_impact", "portfolio_value")
            _rename_key(item, "why_build_this", "why_this_project")
            for dep_key in (
                "career_match_percentage",
                "technology_stack",
                "resume_impact",
                "key_features",
            ):
                item.pop(dep_key, None)

    return ProjectRecommendationPayload(**raw)


def _rename_key(d: dict, old: str, new: str) -> None:
    if old in d and old != new:
        d[new] = d.pop(old)
