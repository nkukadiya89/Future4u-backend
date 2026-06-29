from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from course_generation.services.payload_parser import parse_ai_payload

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_MARKDOWN_FENCE_RE = re.compile(
    r"^```(?:json)?\s*\n?(.*?)\n?```\s*$",
    re.DOTALL | re.IGNORECASE,
)


@dataclass(frozen=True)
class JsonParseValidateResult:
    raw_llm_response: str
    extracted_json: str | None
    parsed_data: dict[str, Any] | None
    parse_error: str | None
    validation_errors: str | None
    validated_model: BaseModel | None = None

    @property
    def success(self) -> bool:
        return self.validated_model is not None

    @property
    def is_json_parse_failure(self) -> bool:
        return self.parse_error is not None

    @property
    def is_schema_validation_failure(self) -> bool:
        return self.parse_error is None and self.validation_errors is not None


class JsonResponseParser:
    """Extract, parse, and validate raw LLM text responses as JSON objects."""

    def parse_and_validate(self, raw: str, *, model_class: type[T]) -> JsonParseValidateResult:
        raw_text = str(raw or "")
        cleaned = self._strip_markdown_fences(raw_text)
        cleaned = self._strip_leading_trailing_text(cleaned)
        extracted = self._extract_first_json_object(cleaned)

        if not extracted:
            result = JsonParseValidateResult(
                raw_llm_response=raw_text,
                extracted_json=None,
                parsed_data=None,
                parse_error="No valid JSON object found in LLM response",
                validation_errors=None,
            )
            self._log_result(result)
            return result

        try:
            parsed = json.loads(extracted)
        except json.JSONDecodeError as exc:
            result = JsonParseValidateResult(
                raw_llm_response=raw_text,
                extracted_json=extracted,
                parsed_data=None,
                parse_error=f"Invalid JSON: {exc.msg} at position {exc.pos}",
                validation_errors=None,
            )
            self._log_result(result)
            return result

        if not isinstance(parsed, dict):
            result = JsonParseValidateResult(
                raw_llm_response=raw_text,
                extracted_json=extracted,
                parsed_data=None,
                parse_error="JSON root must be an object",
                validation_errors=None,
            )
            self._log_result(result)
            return result

        try:
            validated = parse_ai_payload(parsed)
            if not isinstance(validated, model_class):
                validated = model_class.model_validate(validated.model_dump())
        except (ValidationError, ValueError) as exc:
            validation_errors = format_validation_errors(exc)
            result = JsonParseValidateResult(
                raw_llm_response=raw_text,
                extracted_json=extracted,
                parsed_data=parsed,
                parse_error=None,
                validation_errors=validation_errors,
            )
            self._log_result(result)
            return result

        result = JsonParseValidateResult(
            raw_llm_response=raw_text,
            extracted_json=extracted,
            parsed_data=parsed,
            parse_error=None,
            validation_errors=None,
            validated_model=validated,
        )
        self._log_result(result)
        return result

    @classmethod
    def _strip_markdown_fences(cls, text: str) -> str:
        stripped = text.strip()
        match = _MARKDOWN_FENCE_RE.match(stripped)
        if match:
            return match.group(1).strip()

        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines).strip()
        return stripped

    @classmethod
    def _strip_leading_trailing_text(cls, text: str) -> str:
        start = text.find("{")
        if start == -1:
            return text.strip()
        return text[start:].strip()

    @classmethod
    def _extract_first_json_object(cls, text: str) -> str | None:
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape = False

        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
        return None

    @classmethod
    def _log_result(cls, result: JsonParseValidateResult) -> None:
        if result.success:
            return

        logger.warning(
            "LLM JSON parse/validate failed parse_error=%r validation_errors=%r",
            result.parse_error,
            result.validation_errors,
        )


def format_validation_errors(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        items: list[str] = []
        for err in exc.errors()[:8]:
            loc = ".".join(str(part) for part in (err.get("loc") or []) if part is not None)
            msg = _clean_validation_message(str(err.get("msg") or "validation error").strip())
            if loc:
                items.append(f"{loc}: {msg}")
            else:
                items.append(msg)
        text = "; ".join(items).strip()
        return text or "Schema validation failed"
    message = _clean_validation_message(str(exc).strip())
    return message or "Schema validation failed"


def _clean_validation_message(message: str) -> str:
    prefixes = ("Value error, ", "value_error, ")
    for prefix in prefixes:
        if message.startswith(prefix):
            return message[len(prefix) :].strip()
    return message
