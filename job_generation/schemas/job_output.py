from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from job_generation.constants.job_generation_constants import (
    DESCRIPTION_MAX_WORDS,
    DESCRIPTION_MIN_WORDS,
    DESCRIPTION_SENTENCE_COUNT,
    DISALLOWED_PLACEHOLDERS,
    EDUCATION_TAG_MAX_LENGTH,
    EDUCATION_TAGS_MAX,
    EDUCATION_TAGS_MIN,
    RESPONSIBILITIES_COUNT,
    RESPONSIBILITY_ITEM_MAX_WORDS,
    RESPONSIBILITY_ITEM_MIN_WORDS,
    WHY_THIS_MATCH_MAX_WORDS,
    WHY_THIS_MATCH_MIN_WORDS,
    WHY_THIS_MATCH_SENTENCE_COUNT,
)
from job_generation.utils import (
    clip,
    contains_placeholder,
    deduplicate,
    has_broken_punctuation,
    normalize_text,
    sentences,
    word_count,
)


def coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        for sep in ("\n", ";", "|"):
            if sep in text:
                return [p.strip() for p in text.split(sep) if p.strip()]
        if "," in text:
            return [p.strip() for p in text.split(",") if p.strip()]
        return [text]
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, dict):
                text = str(
                    item.get("text") or item.get("name") or item.get("label") or ""
                ).strip()
            else:
                text = str(item).strip()
            if text:
                out.append(text)
        return out
    return [str(value).strip()] if str(value).strip() else []


def _normalize_education_tags(values: list[str]) -> list[str]:
    normalized = [
        clip(str(item or "").strip(), EDUCATION_TAG_MAX_LENGTH)
        for item in values
        if str(item or "").strip()
    ]
    if not normalized:
        raise ValueError("education_tags must contain at least one value")
    deduped = deduplicate(normalized)
    if len(deduped) != len(normalized):
        raise ValueError("education_tags contains duplicate entries")
    return deduped


class JobGenerationPayload(BaseModel):
    """AI-generated fields only (Add Job form). Field names match internship_job.Job."""

    name: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=30, max_length=500)
    responsibilities: list[str] = Field(min_length=RESPONSIBILITIES_COUNT, max_length=RESPONSIBILITIES_COUNT)
    skills: list[str] = Field(min_length=4, max_length=8)
    education_tags: list[str] = Field(min_length=EDUCATION_TAGS_MIN, max_length=EDUCATION_TAGS_MAX)
    why_this_match: str = Field(min_length=20, max_length=300)

    @field_validator("responsibilities", "skills", "education_tags", mode="before")
    @classmethod
    def _list_fields(cls, value: Any) -> list[str]:
        return coerce_string_list(value)

    @field_validator(
        "name",
        "description",
        "why_this_match",
    )
    @classmethod
    def _strip_strings(cls, value: object) -> str:
        return str(value or "").strip()

    @model_validator(mode="after")
    def _normalize_and_validate(self) -> JobGenerationPayload:
        self.name = clip(self.name, 200)
        self.description = clip(self.description, 500)
        self.education_tags = _normalize_education_tags(self.education_tags)
        self.why_this_match = clip(self.why_this_match, 300)

        for field_name in ("responsibilities", "skills"):
            items = [clip(item, 200) for item in getattr(self, field_name) if item.strip()]
            deduped = deduplicate(items)
            if len(deduped) != len(items):
                raise ValueError(f"{field_name} contains duplicate entries")
            setattr(self, field_name, deduped)

        if len(self.education_tags) < EDUCATION_TAGS_MIN:
            raise ValueError(f"education_tags must have at least {EDUCATION_TAGS_MIN} item")
        if len(self.education_tags) > EDUCATION_TAGS_MAX:
            raise ValueError(f"education_tags must have at most {EDUCATION_TAGS_MAX} items")

        if len(self.responsibilities) != RESPONSIBILITIES_COUNT:
            raise ValueError(f"responsibilities must have exactly {RESPONSIBILITIES_COUNT} items")
        for index, item in enumerate(self.responsibilities, start=1):
            item_wc = word_count(item)
            if item_wc < RESPONSIBILITY_ITEM_MIN_WORDS:
                raise ValueError(
                    f"responsibility {index} must be at least "
                    f"{RESPONSIBILITY_ITEM_MIN_WORDS} words"
                )
            if item_wc > RESPONSIBILITY_ITEM_MAX_WORDS:
                raise ValueError(
                    f"responsibility {index} must be <= "
                    f"{RESPONSIBILITY_ITEM_MAX_WORDS} words"
                )

        if len(self.skills) > 8:
            raise ValueError("skills must have at most 8 items")

        if not self.why_this_match.strip():
            raise ValueError("why_this_match must not be empty")

        desc_wc = word_count(self.description)
        if desc_wc > DESCRIPTION_MAX_WORDS:
            raise ValueError(f"description must be <= {DESCRIPTION_MAX_WORDS} words")
        if desc_wc < DESCRIPTION_MIN_WORDS:
            raise ValueError(f"description must be at least {DESCRIPTION_MIN_WORDS} words")

        desc_sentence_count = len(sentences(self.description))
        if desc_sentence_count != DESCRIPTION_SENTENCE_COUNT:
            raise ValueError(
                f"description must be exactly {DESCRIPTION_SENTENCE_COUNT} sentences"
            )

        why_wc = word_count(self.why_this_match)
        if why_wc > WHY_THIS_MATCH_MAX_WORDS:
            raise ValueError(f"why_this_match must be <= {WHY_THIS_MATCH_MAX_WORDS} words")
        if why_wc < WHY_THIS_MATCH_MIN_WORDS:
            raise ValueError(f"why_this_match must be at least {WHY_THIS_MATCH_MIN_WORDS} words")

        why_sentence_count = len(sentences(self.why_this_match))
        if why_sentence_count != WHY_THIS_MATCH_SENTENCE_COUNT:
            raise ValueError(
                f"why_this_match must be exactly {WHY_THIS_MATCH_SENTENCE_COUNT} sentences"
            )

        for text in (self.description, self.why_this_match):
            if contains_placeholder(text, DISALLOWED_PLACEHOLDERS):
                raise ValueError("generated text contains placeholder text")
            if has_broken_punctuation(text):
                raise ValueError("generated text contains broken punctuation")

        desc_sentences = [normalize_text(s) for s in sentences(self.description)]
        if len(desc_sentences) != len(set(desc_sentences)) and len(desc_sentences) > 1:
            raise ValueError("description contains repeated sentences")

        description_norm = normalize_text(self.description)
        for item in self.responsibilities + self.skills:
            item_norm = normalize_text(item)
            if len(item_norm.split()) >= 3 and item_norm in description_norm:
                raise ValueError("description repeats content from other fields")

        return self
