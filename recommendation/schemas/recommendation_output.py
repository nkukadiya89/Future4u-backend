from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from recommendation.config import EASY_DECISION_COUNT, TOP_SUGGESTION_COUNT


def _clip(value: object, max_len: int) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


# Limits shared by the Groq system prompt and post-generation validation/clipping.
WHY_CAREER_MIN_WORDS = 5
WHY_CAREER_MAX_WORDS = 12
WHY_CAREER_MAX_BULLETS = 5
ROADMAP_MIN_WORDS = 8
ROADMAP_MAX_WORDS = 14
AI_INSIGHT_MIN_WORDS = 8
AI_INSIGHT_MAX_WORDS = 18
EDUCATION_SUGGESTION_MIN = 2
EDUCATION_SUGGESTION_MAX = 3

RiskLevel = Literal["Low", "Medium", "High"]

_RISK_LEVEL_ALIASES: dict[str, RiskLevel] = {
    "low": "Low",
    "medium": "Medium",
    "med": "Medium",
    "moderate": "Medium",
    "high": "High",
    "extreme high": "High",
    "extremely high": "High",
    "extream high": "High",
    "very high": "High",
}

def normalize_risk_level(value: object) -> RiskLevel | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    key = " ".join(text.lower().split())
    if key in _RISK_LEVEL_ALIASES:
        return _RISK_LEVEL_ALIASES[key]
    for level in ("Low", "Medium", "High"):
        if level.lower() == key:
            return level
    if "extreme" in key or "extream" in key or "very high" in key:
        return "High"
    if "moderate" in key or "medium" in key:
        return "Medium"
    if "low" in key:
        return "Low"
    if "high" in key:
        return "High"
    return None


def _clip_max_words(value: object, *, max_words: int) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def _coerce_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def clip_why_career_reason(value: object) -> str:
    """Keep why_this_career bullets to at most 7 words."""
    return _clip_max_words(value, max_words=WHY_CAREER_MAX_WORDS)


def clip_roadmap_text(value: object) -> str:
    """Keep roadmap task_title and task_description to at most 14 words."""
    return _clip_max_words(value, max_words=ROADMAP_MAX_WORDS)


def clip_ai_insight(value: object) -> str:
    """Keep ai_insight to at most 18 words."""
    return _clip_max_words(value, max_words=AI_INSIGHT_MAX_WORDS)


def normalize_education_suggestions(raw: list[str]) -> list[str]:
    """Dedupe and clip AI-generated education suggestions."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw:
        text = _clip(str(item).strip(), 255)
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned[:EDUCATION_SUGGESTION_MAX]


class RoadmapTask(BaseModel):
    task_title: str = Field(
        min_length=1,
        max_length=120,
        description="8-14 words only; short actionable phrase.",
    )
    task_description: str = Field(
        min_length=1,
        max_length=200,
        description="8-14 words only; short actionable phrase.",
    )

    @field_validator("task_title", "task_description", mode="before")
    @classmethod
    def clip_roadmap_fields(cls, value: object) -> object:
        return clip_roadmap_text(value)


class CareerRoadmap(BaseModel):
    next_3_months: list[RoadmapTask] = Field(min_length=1, max_length=2)
    next_3_to_6_months: list[RoadmapTask] = Field(min_length=1, max_length=2)
    next_6_to_9_months: list[RoadmapTask] = Field(min_length=1, max_length=2)
    next_9_to_12_months: list[RoadmapTask] = Field(min_length=1, max_length=2)


class RequiredEducation(BaseModel):
    suggestions: list[str] = Field(
        default_factory=list,
        max_length=EDUCATION_SUGGESTION_MAX,
        description="2-3 degree or qualification suggestions for this career.",
    )

    @field_validator("suggestions")
    @classmethod
    def clean_suggestions(cls, value: list[str]) -> list[str]:
        return normalize_education_suggestions(value)


class SalaryFactor(BaseModel):
    average: str | None = Field(default=None, max_length=120)
    growth_rate: str | None = Field(default=None, max_length=200)

    @field_validator("average", mode="before")
    @classmethod
    def clip_average(cls, value: object) -> object:
        if value is None:
            return None
        text = str(value).strip()
        return _clip(text, 120) if text else None

    @field_validator("growth_rate", mode="before")
    @classmethod
    def clip_growth(cls, value: object) -> object:
        if value is None:
            return value
        return _clip(value, 200)


class JobSecurityFactor(BaseModel):
    level: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    market_demand_growth: str | None = Field(default=None, max_length=100)

    @field_validator("level", "market_demand_growth", mode="before")
    @classmethod
    def clip_security_text(cls, value: object) -> object:
        if value is None:
            return value
        return _clip(value, 100)

    @field_validator("description", mode="before")
    @classmethod
    def clip_description(cls, value: object) -> object:
        if value is None:
            return None
        text = str(value).strip()
        return _clip(text, 500) if text else None


class LearningCurveFactor(BaseModel):
    level: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class CareerFactors(BaseModel):
    salary: SalaryFactor | None = None
    growth_potential: str | None = Field(default=None, max_length=200)
    work_life_balance: str | None = Field(default=None, max_length=200)
    job_security: JobSecurityFactor | None = None
    skill_match: int | None = Field(default=None, ge=0, le=100)
    risk_level: RiskLevel | None = Field(
        default=None,
        description='Must be exactly one of: "Low", "Medium", "High".',
    )
    learning_curve: LearningCurveFactor | None = None

    @field_validator("risk_level", mode="before")
    @classmethod
    def normalize_risk(cls, value: object) -> object:
        return normalize_risk_level(value)

    @field_validator("skill_match", mode="before")
    @classmethod
    def coerce_skill_match(cls, value: object) -> object:
        if value is None or value == "":
            return None
        try:
            return max(0, min(100, int(round(float(str(value).strip().rstrip("%"))))))
        except (TypeError, ValueError):
            return None

    @field_validator("growth_potential", "work_life_balance", mode="before")
    @classmethod
    def clip_factor_labels(cls, value: object) -> object:
        if value is None:
            return None
        text = str(value).strip()
        return _clip(text, 200) if text else None


class TopSuggestionItem(BaseModel):
    career_name: str = Field(min_length=1, max_length=255)
    match_percentage: int = Field(ge=0, le=100)
    ai_insight: str = Field(
        min_length=1,
        max_length=200,
        description="14-18 words only; one short personalized sentence.",
    )
    why_this_career: list[str] = Field(
        min_length=1,
        max_length=5,
        description=(
            "Up to 5 short reasons; each reason must be 5-7 words only "
            "(phrase, not a sentence)."
        ),
    )
    required_skills: list[str] = Field(min_length=1, max_length=20)
    required_education: RequiredEducation | None = None
    career_factors: CareerFactors | None = None
    career_roadmap: CareerRoadmap

    @field_validator("match_percentage", mode="before")
    @classmethod
    def coerce_match(cls, value: object) -> object:
        if value is None or value == "":
            raise ValueError("match_percentage is required from AI output")
        try:
            return max(0, min(100, int(round(float(str(value).strip().rstrip("%"))))))
        except (TypeError, ValueError) as exc:
            raise ValueError("match_percentage must be a number") from exc

    @field_validator("why_this_career", mode="before")
    @classmethod
    def coerce_why_list(cls, value: object) -> object:
        if isinstance(value, list):
            return value
        return _coerce_string_list(value)

    @field_validator("required_skills", mode="before")
    @classmethod
    def coerce_skills_list(cls, value: object) -> object:
        if isinstance(value, list):
            return value
        return _coerce_string_list(value)

    @field_validator("ai_insight", mode="before")
    @classmethod
    def clip_insight(cls, value: object) -> object:
        return clip_ai_insight(value)

    @field_validator("why_this_career")
    @classmethod
    def strip_reasons(cls, value: list[str]) -> list[str]:
        cleaned = [clip_why_career_reason(v) for v in value if str(v).strip()]
        cleaned = [c for c in cleaned if c]
        if not cleaned:
            raise ValueError("why_this_career must contain at least one item")
        return cleaned[:5]

    @field_validator("required_skills")
    @classmethod
    def strip_skills(cls, value: list[str]) -> list[str]:
        cleaned = [str(v).strip() for v in value if str(v).strip()]
        if not cleaned:
            raise ValueError("required_skills must contain at least one item")
        return cleaned[:20]


class EasyDecisionItem(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    career_name: str = Field(min_length=1, max_length=255)


class AIRecommendationPayload(BaseModel):
    top_suggestions: list[TopSuggestionItem] = Field(
        min_length=1, max_length=TOP_SUGGESTION_COUNT
    )
    easy_decision_making: list[EasyDecisionItem] = Field(
        min_length=1, max_length=EASY_DECISION_COUNT
    )

    @field_validator("top_suggestions")
    @classmethod
    def limit_unique_suggestions(
        cls, value: list[TopSuggestionItem]
    ) -> list[TopSuggestionItem]:
        trimmed = value[:TOP_SUGGESTION_COUNT]
        names = [
            item.career_name.strip().casefold()
            for item in trimmed
            if item.career_name.strip()
        ]
        if len(names) != len(set(names)):
            raise ValueError(
                "top_suggestions must not contain duplicate career_name values"
            )
        return trimmed

    @field_validator("easy_decision_making", mode="before")
    @classmethod
    def limit_decisions(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        cleaned: list[object] = []
        for item in value[:EASY_DECISION_COUNT]:
            if isinstance(item, dict):
                item = {k: v for k, v in item.items() if k != "reason"}
            cleaned.append(item)
        return cleaned
