from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from internship_generation.constants.internship_generation_constants import (
    ABOUT_INTERNSHIP_MAX_WORDS,
    ABOUT_INTERNSHIP_MIN_WORDS,
    BANNED_MARKETING_PHRASES,
    BANNED_TITLE_PHRASES,
    DISALLOWED_PLACEHOLDERS,
    INTERNSHIP_TITLE_MAX_LENGTH,
    INTERNSHIP_TITLE_MIN_LENGTH,
    RESPONSIBILITIES_MAX,
    RESPONSIBILITIES_MIN,
    RESPONSIBILITY_ITEM_MAX_LENGTH,
    SKILLS_MAX,
    SKILLS_MIN,
    SKILL_ITEM_MAX_LENGTH,
)
from internship_generation.utils import (
    clip,
    contains_banned_phrase,
    contains_placeholder,
    deduplicate,
    has_broken_punctuation,
    normalize_text,
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


class InternshipGenerationPayload(BaseModel):
    """AI-generated fields only (Post Internship form)."""

    internship_title: str = Field(
        min_length=INTERNSHIP_TITLE_MIN_LENGTH,
        max_length=INTERNSHIP_TITLE_MAX_LENGTH,
    )
    about_internship: str = Field(min_length=10, max_length=600)
    key_responsibilities: list[str] = Field(
        min_length=RESPONSIBILITIES_MIN,
        max_length=RESPONSIBILITIES_MAX,
    )
    skills: list[str] = Field(min_length=SKILLS_MIN, max_length=SKILLS_MAX)

    @field_validator("key_responsibilities", "skills", mode="before")
    @classmethod
    def _list_fields(cls, value: Any) -> list[str]:
        return coerce_string_list(value)

    @field_validator("internship_title", "about_internship")
    @classmethod
    def _strip_strings(cls, value: object) -> str:
        return str(value or "").strip()

    @model_validator(mode="after")
    def _normalize_and_validate(self) -> InternshipGenerationPayload:
        self.internship_title = clip(self.internship_title, INTERNSHIP_TITLE_MAX_LENGTH)
        self.about_internship = clip(self.about_internship, 600)

        for field_name, max_len in (
            ("key_responsibilities", RESPONSIBILITY_ITEM_MAX_LENGTH),
            ("skills", SKILL_ITEM_MAX_LENGTH),
        ):
            items = [
                clip(item, max_len)
                for item in getattr(self, field_name)
                if item.strip()
            ]
            deduped = deduplicate(items)
            if len(deduped) != len(items):
                raise ValueError(f"{field_name} contains duplicate entries")
            setattr(self, field_name, deduped)

        if len(self.key_responsibilities) < RESPONSIBILITIES_MIN:
            raise ValueError(
                f"key_responsibilities must have at least {RESPONSIBILITIES_MIN} items"
            )
        if len(self.key_responsibilities) > RESPONSIBILITIES_MAX:
            raise ValueError(
                f"key_responsibilities must have at most {RESPONSIBILITIES_MAX} items"
            )

        if len(self.skills) < SKILLS_MIN:
            raise ValueError(f"skills must have at least {SKILLS_MIN} items")
        if len(self.skills) > SKILLS_MAX:
            raise ValueError(f"skills must have at most {SKILLS_MAX} items")

        # --- about_internship rules ---
        about_wc = word_count(self.about_internship)
        if about_wc > ABOUT_INTERNSHIP_MAX_WORDS:
            raise ValueError(
                f"about_internship must be at most {ABOUT_INTERNSHIP_MAX_WORDS} words "
                f"(got {about_wc})"
            )
        if about_wc < ABOUT_INTERNSHIP_MIN_WORDS:
            raise ValueError(
                f"about_internship must be at least {ABOUT_INTERNSHIP_MIN_WORDS} words "
                f"(got {about_wc})"
            )

        # Must be a single paragraph (no blank lines / double newlines)
        import re as _re
        if _re.search(r"\n\s*\n", self.about_internship):
            raise ValueError("about_internship must be a single paragraph (no blank lines)")

        title_lower = self.internship_title.casefold()
        for phrase in BANNED_TITLE_PHRASES:
            if phrase in title_lower:
                raise ValueError("internship_title contains disallowed marketing language")

        if contains_placeholder(self.internship_title, DISALLOWED_PLACEHOLDERS):
            raise ValueError("internship_title contains placeholder text")
        if contains_placeholder(self.about_internship, DISALLOWED_PLACEHOLDERS):
            raise ValueError("about_internship contains placeholder text")

        if has_broken_punctuation(self.about_internship):
            raise ValueError("about_internship contains broken punctuation")
        if contains_banned_phrase(self.about_internship, BANNED_MARKETING_PHRASES):
            raise ValueError("about_internship contains disallowed marketing language")

        for item in self.key_responsibilities + self.skills:
            if contains_placeholder(item, DISALLOWED_PLACEHOLDERS):
                raise ValueError("list item contains placeholder text")
            if has_broken_punctuation(item):
                raise ValueError("list item contains broken punctuation")

        # about_internship must not copy responsibilities or skills verbatim
        about_norm = normalize_text(self.about_internship)
        for item in self.skills + self.key_responsibilities:
            item_norm = normalize_text(item)
            if len(item_norm.split()) >= 4 and item_norm in about_norm:
                raise ValueError(
                    "about_internship copies verbatim content from skills or key_responsibilities"
                )

        return self
