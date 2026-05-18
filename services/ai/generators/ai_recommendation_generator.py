from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage
from pydantic import ValidationError

from services.ai.clients.llm_client import get_chat_model
from services.ai.config import TOP_SUGGESTION_COUNT
from services.ai.exceptions import AIGenerationError
from services.ai.prompts.ai_recommendation_prompt import (
    build_recommendation_prompt,
    format_prompt_inputs,
)
from services.ai.schemas.recommendation_output import AIRecommendationPayload

logger = logging.getLogger(__name__)

_STRUCTURED_METHODS = ("json_mode", None)


class AIRecommendationGenerator:
    """Full AI recommendations from student_signals + career_candidates."""

    @classmethod
    def generate(
        cls,
        *,
        student_signals: dict[str, Any],
        career_candidates: list[dict[str, Any]],
    ) -> AIRecommendationPayload:
        if not career_candidates:
            raise AIGenerationError(
                "No career candidates found for the selected domain"
            )

        prompt = build_recommendation_prompt()
        inputs = format_prompt_inputs(
            student_signals=student_signals,
            career_candidates=career_candidates,
        )
        llm = get_chat_model()
        return cls._generate_with_llm(
            prompt=prompt,
            inputs=inputs,
            llm=llm,
            career_candidates=career_candidates,
        )

    @classmethod
    def _generate_with_llm(
        cls,
        *,
        prompt,
        inputs: dict[str, Any],
        llm,
        career_candidates: list[dict[str, Any]],
    ) -> AIRecommendationPayload:
        errors: list[str] = []

        for method in _STRUCTURED_METHODS:
            try:
                payload = cls._invoke_structured(
                    prompt=prompt, inputs=inputs, llm=llm, method=method
                )
                if cls._has_valid_shape(payload, career_candidates):
                    return payload
                errors.append(f"groq ({method or 'default'}): incomplete schema")
            except ValidationError as exc:
                logger.warning("Groq output validation failed (%s): %s", method, exc)
                errors.append(f"groq ({method or 'default'}): validation failed")
            except Exception as exc:
                if _is_function_call_error(exc):
                    logger.warning(
                        "Groq function-call structured output failed (%s): %s",
                        method,
                        exc,
                    )
                    errors.append(f"groq ({method or 'default'}): function call failed")
                    continue
                logger.exception("Groq recommendation generation failed")
                raise AIGenerationError(_format_groq_error(exc)) from exc

        try:
            payload = cls._invoke_json_fallback(prompt=prompt, inputs=inputs, llm=llm)
            if cls._has_valid_shape(payload, career_candidates):
                return payload
            errors.append("groq: JSON fallback returned incomplete schema")
        except Exception as exc:
            logger.warning("Groq JSON fallback failed: %s", exc)
            errors.append("groq: JSON fallback failed")

        detail = "; ".join(errors) if errors else "unknown error"
        raise AIGenerationError(
            f"AI could not produce valid recommendations ({detail}). Retry shortly."
        )

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
        if isinstance(result, AIRecommendationPayload):
            return result
        return AIRecommendationPayload.model_validate(result)

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
        return AIRecommendationPayload.model_validate_json(raw[start : end + 1])

    @staticmethod
    def _has_valid_shape(
        payload: AIRecommendationPayload,
        career_candidates: list[dict[str, Any]],
    ) -> bool:
        if not payload.top_suggestions:
            return False
        if len(payload.top_suggestions) > TOP_SUGGESTION_COUNT:
            return False

        expected = {
            str(row.get("career_name", "")).strip().casefold()
            for row in career_candidates
            if row.get("career_name")
        }
        returned = {
            item.career_name.strip().casefold() for item in payload.top_suggestions
        }
        if expected and not returned.intersection(expected):
            return False

        first = payload.top_suggestions[0]
        roadmap = first.career_roadmap
        if len(first.why_this_career) > 5:
            return False
        return bool(
            first.career_name.strip()
            and first.match_percentage > 0
            and first.ai_insight.strip()
            and first.why_this_career
            and first.required_skills
            and roadmap.next_3_months
            and roadmap.next_3_to_6_months
            and roadmap.next_6_to_9_months
            and roadmap.next_9_to_12_months
            and len(payload.easy_decision_making) >= 1
        )


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
