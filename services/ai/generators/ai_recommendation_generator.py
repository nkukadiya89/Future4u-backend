from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage
from pydantic import ValidationError

from services.ai.clients.llm_client import get_chat_model
from services.ai.config import EASY_DECISION_COUNT, TOP_SUGGESTION_COUNT
from services.ai.exceptions import AIGenerationError
from services.ai.pipeline.payload_validator import parse_ai_payload, parse_ai_payload_lenient
from services.ai.prompts.ai_recommendation_prompt import (
    RETRY_FORMAT_REMINDER,
    build_recommendation_prompt,
    format_prompt_inputs,
)
from services.ai.schemas.recommendation_output import (
    AIRecommendationPayload,
    WHY_CAREER_MAX_BULLETS,
    is_valid_ai_insight,
    is_valid_education_suggestions,
)

logger = logging.getLogger(__name__)

_STRUCTURED_METHODS = ("json_mode", None)
_MAX_VALIDATION_RETRIES = 2


class AIRecommendationGenerator:
    """Full AI recommendations from student_signals only (Groq picks all careers)."""

    @classmethod
    def generate(cls, *, student_signals: dict[str, Any]) -> AIRecommendationPayload:
        prompt = build_recommendation_prompt()
        inputs = format_prompt_inputs(student_signals=student_signals)
        llm = get_chat_model()
        return cls._generate_with_llm(prompt=prompt, inputs=inputs, llm=llm)

    @classmethod
    def _generate_with_llm(cls, *, prompt, inputs: dict[str, Any], llm) -> AIRecommendationPayload:
        errors: list[str] = []

        for attempt in range(_MAX_VALIDATION_RETRIES + 1):
            retry_inputs = cls._inputs_for_attempt(inputs, attempt)
            for method in _STRUCTURED_METHODS:
                try:
                    payload = cls._invoke_structured(
                        prompt=prompt,
                        inputs=retry_inputs,
                        llm=llm,
                        method=method,
                    )
                    if cls._has_valid_shape(payload):
                        return payload
                    errors.append(
                        f"groq ({method or 'default'}, attempt {attempt + 1}): "
                        "incomplete schema"
                    )
                except ValidationError as exc:
                    logger.warning(
                        "Groq output validation failed (%s, attempt %s): %s",
                        method,
                        attempt + 1,
                        exc,
                    )
                    errors.append(
                        f"groq ({method or 'default'}, attempt {attempt + 1}): "
                        "validation failed"
                    )
                except Exception as exc:
                    if _is_function_call_error(exc):
                        logger.warning(
                            "Groq function-call structured output failed (%s): %s",
                            method,
                            exc,
                        )
                        errors.append(
                            f"groq ({method or 'default'}): function call failed"
                        )
                        continue
                    logger.exception("Groq recommendation generation failed")
                    raise AIGenerationError(_format_groq_error(exc)) from exc

            try:
                payload = cls._invoke_json_fallback(
                    prompt=prompt, inputs=retry_inputs, llm=llm
                )
                if cls._has_valid_shape(payload):
                    return payload
                errors.append(
                    f"groq: JSON fallback incomplete schema (attempt {attempt + 1})"
                )
            except ValidationError as exc:
                logger.warning(
                    "Groq JSON fallback validation failed (attempt %s): %s",
                    attempt + 1,
                    exc,
                )
                errors.append(
                    f"groq: JSON fallback validation failed (attempt {attempt + 1})"
                )
            except Exception as exc:
                logger.warning(
                    "Groq JSON fallback failed (attempt %s): %s", attempt + 1, exc
                )
                errors.append(f"groq: JSON fallback failed (attempt {attempt + 1})")

        detail = "; ".join(errors) if errors else "unknown error"
        raise AIGenerationError(
            f"AI could not produce valid recommendations ({detail}). Retry shortly."
        )

    @staticmethod
    def _inputs_for_attempt(inputs: dict[str, Any], attempt: int) -> dict[str, Any]:
        if attempt == 0:
            return inputs
        merged = dict(inputs)
        merged["format_reminder"] = RETRY_FORMAT_REMINDER
        return merged

    @classmethod
    def _invoke_structured(
        cls,
        *,
        prompt,
        inputs: dict[str, Any],
        llm,
        method: str | None,
    ) -> AIRecommendationPayload:
        if method:
            structured_llm = llm.with_structured_output(
                AIRecommendationPayload,
                method=method,
            )
        else:
            structured_llm = llm.with_structured_output(AIRecommendationPayload)

        chain = prompt | structured_llm
        result = chain.invoke(inputs)
        return cls._coerce_payload(result)

    @classmethod
    def _invoke_json_fallback(
        cls,
        *,
        prompt,
        inputs: dict[str, Any],
        llm,
    ) -> AIRecommendationPayload:
        schema_hint = json.dumps(
            AIRecommendationPayload.model_json_schema(),
            ensure_ascii=True,
        )[:8000]
        json_prompt = prompt.partial(
            output_shape=(
                "Return ONLY valid JSON (no markdown). Schema summary:\n" + schema_hint
            )
        )
        messages = json_prompt.format_messages(**inputs)
        messages.append(
            HumanMessage(
                content="Respond with a single JSON object only. No code fences or commentary."
            )
        )
        response = llm.invoke(messages)
        text = response.content if isinstance(response.content, str) else str(response.content)
        return cls._parse_json_payload(text)

    @staticmethod
    def _coerce_payload(result: Any) -> AIRecommendationPayload:
        payload = parse_ai_payload_lenient(result)
        if payload is not None:
            return payload
        return parse_ai_payload(result)

    @classmethod
    def _parse_json_payload(cls, text: str) -> AIRecommendationPayload:
        raw = text.strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
        if fence:
            raw = fence.group(1).strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise AIGenerationError("AI response did not contain JSON")
        data = json.loads(raw[start : end + 1])
        payload = parse_ai_payload_lenient(data)
        if payload is not None:
            return payload
        return parse_ai_payload(data)

    @staticmethod
    def _has_valid_shape(payload: AIRecommendationPayload) -> bool:
        if len(payload.top_suggestions) != TOP_SUGGESTION_COUNT:
            return False
        if len(payload.easy_decision_making) != EASY_DECISION_COUNT:
            return False

        returned_names = [
            item.career_name.strip().casefold() for item in payload.top_suggestions
        ]
        if len(returned_names) != TOP_SUGGESTION_COUNT:
            return False
        if len(set(returned_names)) != TOP_SUGGESTION_COUNT:
            return False

        skill_sets: list[frozenset[str]] = []
        roadmap_signatures: list[tuple[str, ...]] = []

        for item in payload.top_suggestions:
            roadmap = item.career_roadmap
            if not (
                item.career_name.strip()
                and item.match_percentage > 0
                and is_valid_ai_insight(item.ai_insight)
                and item.why_this_career
                and len(item.why_this_career) <= WHY_CAREER_MAX_BULLETS
                and item.required_skills
                and item.required_education
                and is_valid_education_suggestions(
                    item.required_education.suggestions
                )
                and roadmap.next_3_months
                and roadmap.next_3_to_6_months
                and roadmap.next_6_to_9_months
                and roadmap.next_9_to_12_months
            ):
                return False

            skill_sets.append(
                frozenset(s.strip().casefold() for s in item.required_skills if s.strip())
            )
            roadmap_signatures.append(
                tuple(
                    task.task_title.strip().casefold()
                    for phase in (
                        roadmap.next_3_months,
                        roadmap.next_3_to_6_months,
                        roadmap.next_6_to_9_months,
                        roadmap.next_9_to_12_months,
                    )
                    for task in phase
                )
            )

        if len(skill_sets) != len(set(skill_sets)):
            return False
        if len(roadmap_signatures) != len(set(roadmap_signatures)):
            return False

        return True


def _is_function_call_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "failed to call a function" in message or (
        "error code: 400" in message and "function" in message
    )


def _format_groq_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    if _is_function_call_error(exc):
        return (
            "Groq could not use tool-based JSON output. "
            "Retry the request; the server uses JSON mode automatically."
        )
    if "429" in message:
        return "Groq rate limit reached. Retry in a few moments."
    return message
