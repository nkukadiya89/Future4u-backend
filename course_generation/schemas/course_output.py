from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from course_generation.constants.course_generation_constants import (
    BANNED_JOB_PROMISE_PHRASES,
    BANNED_MARKETING_PHRASES,
    BANNED_TITLE_PHRASES,
    CERTIFICATION_INFO_MAX_WORDS,
    CERTIFICATION_INFO_MIN_WORDS,
    COURSE_CONTENT_ITEM_MAX_LENGTH,
    COURSE_CONTENT_MAX,
    COURSE_CONTENT_MIN,
    COURSE_TITLE_MAX_LENGTH,
    COURSE_TITLE_MIN_LENGTH,
    DISALLOWED_PLACEHOLDERS,
    INVENTED_CERT_PROVIDERS,
    OVERVIEW_MAX_WORDS,
    OVERVIEW_MIN_WORDS,
    SKILLS_ITEM_MAX_WORDS,
    SKILLS_MAX,
    SKILLS_MIN,
    WHY_THIS_COURSE_MAX_WORDS,
    WHY_THIS_COURSE_MIN_WORDS,
)
from course_generation.utils import (
    clip,
    contains_banned_phrase,
    contains_invented_cert_provider,
    contains_placeholder,
    count_overview_repeated_items,
    deduplicate,
    has_broken_punctuation,
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


class CourseGenerationPayload(BaseModel):
    """AI-generated fields only (Add Course form)."""

    course_title: str = Field(min_length=COURSE_TITLE_MIN_LENGTH, max_length=COURSE_TITLE_MAX_LENGTH)
    course_overview: str = Field(min_length=30, max_length=2000)
    skills: list[str] = Field(min_length=SKILLS_MIN, max_length=SKILLS_MAX)
    course_content: list[str] = Field(min_length=COURSE_CONTENT_MIN, max_length=COURSE_CONTENT_MAX)
    why_this_course: str = Field(min_length=20, max_length=600)
    certification_info: str = Field(min_length=10, max_length=400)

    @field_validator("skills", "course_content", mode="before")
    @classmethod
    def _list_fields(cls, value: Any) -> list[str]:
        return coerce_string_list(value)

    @field_validator(
        "course_title",
        "course_overview",
        "why_this_course",
        "certification_info",
    )
    @classmethod
    def _strip_strings(cls, value: object) -> str:
        return str(value or "").strip()

    @model_validator(mode="after")
    def _normalize_and_validate(self) -> CourseGenerationPayload:
        self.course_title = clip(self.course_title, COURSE_TITLE_MAX_LENGTH)
        self.course_overview = clip(self.course_overview, 2000)
        self.why_this_course = clip(self.why_this_course, 600)
        self.certification_info = clip(self.certification_info, 400)

        for field_name in ("skills", "course_content"):
            items = [
                clip(item, COURSE_CONTENT_ITEM_MAX_LENGTH)
                for item in getattr(self, field_name)
                if item.strip()
            ]
            deduped = deduplicate(items)
            if len(deduped) != len(items):
                raise ValueError(f"{field_name} contains duplicate entries")
            setattr(self, field_name, deduped)

        if len(self.skills) < SKILLS_MIN:
            raise ValueError(f"skills must have at least {SKILLS_MIN} items")
        if len(self.skills) > SKILLS_MAX:
            raise ValueError(f"skills must have at most {SKILLS_MAX} items")

        if len(self.course_content) < COURSE_CONTENT_MIN:
            raise ValueError(f"course_content must have at least {COURSE_CONTENT_MIN} items")
        if len(self.course_content) > COURSE_CONTENT_MAX:
            raise ValueError(f"course_content must have at most {COURSE_CONTENT_MAX} items")

        for index, item in enumerate(self.skills, start=1):
            if word_count(item) > SKILLS_ITEM_MAX_WORDS:
                raise ValueError(f"skills item {index} must be a short skill tag")
            if "(" in item or ")" in item:
                raise ValueError(f"skills item {index} must not include parenthetical text")

        for index, item in enumerate(self.course_content, start=1):
            if word_count(item) > 12:
                raise ValueError(f"course_content item {index} must be a short module title")

        overview_wc = word_count(self.course_overview)
        if overview_wc > OVERVIEW_MAX_WORDS:
            raise ValueError(f"course_overview must be <= {OVERVIEW_MAX_WORDS} words")
        if overview_wc < OVERVIEW_MIN_WORDS:
            raise ValueError(f"course_overview must be at least {OVERVIEW_MIN_WORDS} words")

        if "\n\n" in self.course_overview or self.course_overview.count("\n") >= 2:
            raise ValueError("course_overview must be a single paragraph with no line breaks")

        why_wc = word_count(self.why_this_course)
        if why_wc > WHY_THIS_COURSE_MAX_WORDS:
            raise ValueError(f"why_this_course must be <= {WHY_THIS_COURSE_MAX_WORDS} words")
        if why_wc < WHY_THIS_COURSE_MIN_WORDS:
            raise ValueError(f"why_this_course must be at least {WHY_THIS_COURSE_MIN_WORDS} words")

        if "\n\n" in self.why_this_course or self.why_this_course.count("\n") >= 2:
            raise ValueError("why_this_course must be a single paragraph with no line breaks")

        if contains_banned_phrase(self.why_this_course, BANNED_JOB_PROMISE_PHRASES):
            raise ValueError("why_this_course must not mention guaranteed jobs or salaries")

        cert_wc = word_count(self.certification_info)
        if cert_wc > CERTIFICATION_INFO_MAX_WORDS:
            raise ValueError(
                f"certification_info must be <= {CERTIFICATION_INFO_MAX_WORDS} words"
            )
        if cert_wc < CERTIFICATION_INFO_MIN_WORDS:
            raise ValueError(
                f"certification_info must be at least {CERTIFICATION_INFO_MIN_WORDS} words"
            )

        title_lower = self.course_title.casefold()
        for phrase in BANNED_TITLE_PHRASES:
            if phrase in title_lower:
                raise ValueError("course_title contains disallowed marketing language")

        for text in (
            self.course_overview,
            self.why_this_course,
            self.certification_info,
        ):
            if contains_placeholder(text, DISALLOWED_PLACEHOLDERS):
                raise ValueError("generated text contains placeholder text")
            if has_broken_punctuation(text):
                raise ValueError("generated text contains broken punctuation")
            if contains_banned_phrase(text, BANNED_MARKETING_PHRASES):
                raise ValueError("generated text contains disallowed marketing language")

        if contains_invented_cert_provider(self.certification_info, INVENTED_CERT_PROVIDERS):
            raise ValueError("certification_info must not name external certificate providers")

        if count_overview_repeated_items(self.course_overview, self.course_content) >= 2:
            raise ValueError("course_overview repeats content from skills or course_content")

        return self
