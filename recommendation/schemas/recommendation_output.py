from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from recommendation.config import EASY_DECISION_COUNT, TOP_SUGGESTION_COUNT


def _clip(value: object, max_len: int) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


# Limits shared by the AI prompt and post-generation validation/clipping.
WHY_CAREER_MIN_WORDS = 5
WHY_CAREER_MAX_WORDS = 12
WHY_CAREER_MAX_BULLETS = 5
ROADMAP_MIN_WORDS = 8
ROADMAP_TITLE_MAX_WORDS = 14
ROADMAP_MAX_WORDS = 24
AI_INSIGHT_MIN_WORDS = 8
AI_INSIGHT_MAX_WORDS = 18
EDUCATION_SUGGESTION_MIN = 2
EDUCATION_SUGGESTION_MAX = 3

RiskLevel = Literal["Low", "Medium", "High"]
GrowthPotentialLevel = Literal["Low", "Medium", "High"]
WorkLifeBalanceLevel = Literal["Poor", "Fair", "Good", "Excellent"]
JobSecurityLevel = Literal["Low", "Medium", "High"]
LearningCurveLevel = Literal["Low", "Medium", "High"]

EducationLevelKey = Literal[
    "secondary",
    "higher_secondary",
    "diploma",
    "graduation",
    "post_graduation",
    "doctorate",
    "professional",
    "certification",
]

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


_GROWTH_POTENTIAL_ALIASES: dict[str, GrowthPotentialLevel] = dict(_RISK_LEVEL_ALIASES)

_WORK_LIFE_BALANCE_ALIASES: dict[str, WorkLifeBalanceLevel] = {
    "poor": "Poor",
    "bad": "Poor",
    "low": "Poor",
    "weak": "Poor",
    "challenging": "Poor",
    "demanding": "Poor",
    "stressful": "Poor",
    "fair": "Fair",
    "average": "Fair",
    "moderate": "Fair",
    "medium": "Fair",
    "med": "Fair",
    "okay": "Fair",
    "ok": "Fair",
    "good": "Good",
    "balanced": "Good",
    "healthy": "Good",
    "positive": "Good",
    "excellent": "Excellent",
    "great": "Excellent",
    "strong": "Excellent",
    "very good": "Excellent",
    "variable": "Fair",
}


def _factor_label_key(value: object) -> str:
    text = str(value).strip()
    if not text:
        return ""
    for sep in ("—", "–", "-", ",", "|", ":"):
        if sep in text:
            text = text.split(sep, 1)[0].strip()
            break
    return " ".join(text.lower().split())


def normalize_growth_potential(value: object) -> GrowthPotentialLevel | None:
    if value is None:
        return None
    if isinstance(value, dict):
        nested = value.get("level") or value.get("label") or value.get("rating")
        if nested is not None:
            return normalize_growth_potential(nested)
        return None
    key = _factor_label_key(value)
    if not key:
        return None
    if key in _GROWTH_POTENTIAL_ALIASES:
        return _GROWTH_POTENTIAL_ALIASES[key]
    for level in ("Low", "Medium", "High"):
        if level.lower() == key:
            return level
    return normalize_risk_level(value)


def normalize_work_life_balance(value: object) -> WorkLifeBalanceLevel | None:
    if value is None:
        return None
    if isinstance(value, dict):
        nested = value.get("level") or value.get("label") or value.get("rating")
        if nested is not None:
            return normalize_work_life_balance(nested)
        return None
    key = _factor_label_key(value)
    if not key:
        return None
    if key in _WORK_LIFE_BALANCE_ALIASES:
        return _WORK_LIFE_BALANCE_ALIASES[key]
    for level in ("Poor", "Fair", "Good", "Excellent"):
        if level.lower() == key:
            return level
    if "excellent" in key or "great" in key:
        return "Excellent"
    if "good" in key or "balance" in key:
        return "Good"
    if "fair" in key or "moderate" in key or "average" in key:
        return "Fair"
    if "poor" in key or "bad" in key or "demanding" in key or "long hour" in key:
        return "Poor"
    return None


_LEARNING_CURVE_ALIASES: dict[str, LearningCurveLevel] = {
    "low": "Low",
    "easy": "Low",
    "beginner": "Low",
    "medium": "Medium",
    "moderate": "Medium",
    "med": "Medium",
    "high": "High",
    "steep": "High",
    "hard": "High",
    "difficult": "High",
}


def normalize_learning_curve_level(value: object) -> LearningCurveLevel | None:
    if value is None:
        return None
    if isinstance(value, dict):
        nested = value.get("level") or value.get("label") or value.get("curve")
        if nested is not None:
            return normalize_learning_curve_level(nested)
        return None
    key = _factor_label_key(value)
    if not key:
        return None
    if key in _LEARNING_CURVE_ALIASES:
        return _LEARNING_CURVE_ALIASES[key]
    for level in ("Low", "Medium", "High"):
        if level.lower() == key:
            return level
    return normalize_risk_level(value)


def _clip_max_words(value: object, *, max_words: int) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def _clip_sentence_words(value: object, *, max_words: int) -> str:
    text = _clip_max_words(value, max_words=max_words)
    if not text:
        return ""
    words = text.split()
    while words and words[-1].strip(".,;:").casefold() in {
        "and",
        "or",
        "but",
        "with",
        "for",
        "to",
        "in",
        "of",
        "by",
        "before",
    }:
        words.pop()
    text = " ".join(words).rstrip(" ,;:")
    if text and text[-1] not in ".!?":
        text += "."
    return text


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
    """Keep why_this_career bullets to at most 12 words."""
    return _clip_max_words(value, max_words=WHY_CAREER_MAX_WORDS)


def clip_roadmap_title(value: object) -> str:
    """Keep roadmap task_title compact."""
    return _clip_max_words(value, max_words=ROADMAP_TITLE_MAX_WORDS)


def clip_roadmap_description(value: object) -> str:
    """Keep roadmap task_description readable but short."""
    return _clip_max_words(value, max_words=ROADMAP_MAX_WORDS)


def clip_ai_insight(value: object) -> str:
    """Keep ai_insight to at most 18 words."""
    return _clip_sentence_words(value, max_words=AI_INSIGHT_MAX_WORDS)


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
        description="8-24 words only; complete student-friendly sentence.",
    )

    @field_validator("task_title", mode="before")
    @classmethod
    def clip_roadmap_title_field(cls, value: object) -> object:
        return clip_roadmap_title(value)

    @field_validator("task_description", mode="before")
    @classmethod
    def clip_roadmap_description_field(cls, value: object) -> object:
        return clip_roadmap_description(value)


class CareerRoadmap(BaseModel):
    next_3_months: list[RoadmapTask] = Field(min_length=1, max_length=2)
    next_3_to_6_months: list[RoadmapTask] = Field(min_length=1, max_length=2)
    next_6_to_9_months: list[RoadmapTask] = Field(min_length=1, max_length=2)
    next_9_to_12_months: list[RoadmapTask] = Field(min_length=1, max_length=2)


class EducationLevel(BaseModel):
    type: str = Field(min_length=1, max_length=100, description="Display label.")
    level_key: EducationLevelKey = Field(
        description="Standardized education level key."
    )
    name: str = Field(min_length=1, max_length=255, description="Degree/course name.")

    @field_validator("type", "name", mode="before")
    @classmethod
    def strip_fields(cls, value: object) -> object:
        return str(value or "").strip()


class RequiredEducation(BaseModel):
    levels: list[EducationLevel] = Field(
        default_factory=list,
        description="Structured education requirements; always an array.",
    )


class SalaryFactor(BaseModel):
    average: str = Field(
        min_length=1,
        max_length=120,
        description='Annual salary for UI, e.g. "INR 6-10 LPA" or "INR 18L+".',
    )
    growth_rate: str = Field(
        min_length=1,
        max_length=50,
        description='Salary growth badge for UI, e.g. "(+125%)" or "(+10%)".',
    )

    @field_validator("average", mode="before")
    @classmethod
    def clip_average(cls, value: object) -> object:
        text = str(value).strip()
        if not text:
            raise ValueError("salary.average is required from AI output")
        return _clip(text, 120)

    @field_validator("growth_rate", mode="before")
    @classmethod
    def clip_growth(cls, value: object) -> object:
        text = str(value).strip()
        if not text:
            raise ValueError("salary.growth_rate is required from AI output")
        return _clip(text, 50)


class JobSecurityFactor(BaseModel):
    level: JobSecurityLevel = Field(
        description='Job security label for UI: "Low", "Medium", or "High".',
    )
    market_demand_growth: str = Field(
        min_length=1,
        max_length=100,
        description='Demand trend for UI subtitle, e.g. "5% | 25%".',
    )

    @field_validator("level", mode="before")
    @classmethod
    def normalize_level(cls, value: object) -> object:
        normalized = normalize_risk_level(value)
        if normalized is None:
            raise ValueError('job_security.level must be "Low", "Medium", or "High"')
        return normalized

    @field_validator("market_demand_growth", mode="before")
    @classmethod
    def clip_demand_trend(cls, value: object) -> object:
        text = str(value).strip()
        if not text:
            raise ValueError(
                "job_security.market_demand_growth is required from AI output"
            )
        return _clip(text, 100)


class LearningCurveFactor(BaseModel):
    level: LearningCurveLevel = Field(
        description='Learning curve label for UI: "Low", "Medium", or "High".',
    )
    description: str = Field(
        min_length=1,
        max_length=200,
        description='Short UI subtitle, e.g. "To become proficient".',
    )

    @field_validator("level", mode="before")
    @classmethod
    def normalize_level(cls, value: object) -> object:
        normalized = normalize_learning_curve_level(value)
        if normalized is None:
            raise ValueError('learning_curve.level must be "Low", "Medium", or "High"')
        return normalized

    @field_validator("description", mode="before")
    @classmethod
    def clip_description(cls, value: object) -> object:
        text = str(value).strip()
        if not text:
            raise ValueError("learning_curve.description is required from AI output")
        return _clip(text, 200)


class CareerFactors(BaseModel):
    """Career Factors card; field order matches mobile UI rows."""

    salary: SalaryFactor
    growth_potential: GrowthPotentialLevel = Field(
        description='UI row label value: "Low", "Medium", or "High".',
    )
    work_life_balance: WorkLifeBalanceLevel = Field(
        description='UI row label value: "Poor", "Fair", "Good", or "Excellent".',
    )
    job_security: JobSecurityFactor
    skill_match: int = Field(ge=0, le=100, description="Integer 0-100; UI appends %.")
    learning_curve: LearningCurveFactor
    risk_level: RiskLevel = Field(
        description='UI row label value: "Low", "Medium", or "High".',
    )

    @field_validator("risk_level", mode="before")
    @classmethod
    def normalize_risk(cls, value: object) -> object:
        normalized = normalize_risk_level(value)
        if normalized is None:
            raise ValueError('risk_level must be "Low", "Medium", or "High"')
        return normalized

    @field_validator("skill_match", mode="before")
    @classmethod
    def coerce_skill_match(cls, value: object) -> object:
        if value is None or value == "":
            raise ValueError("skill_match is required from AI output")
        try:
            return max(0, min(100, int(round(float(str(value).strip().rstrip("%"))))))
        except (TypeError, ValueError) as exc:
            raise ValueError("skill_match must be an integer 0-100") from exc

    @field_validator("growth_potential", mode="before")
    @classmethod
    def normalize_growth(cls, value: object) -> object:
        normalized = normalize_growth_potential(value)
        if normalized is None:
            raise ValueError('growth_potential must be "Low", "Medium", or "High"')
        return normalized

    @field_validator("work_life_balance", mode="before")
    @classmethod
    def normalize_balance(cls, value: object) -> object:
        normalized = normalize_work_life_balance(value)
        if normalized is None:
            raise ValueError(
                'work_life_balance must be "Poor", "Fair", "Good", or "Excellent"'
            )
        return normalized


class TopSuggestionItem(BaseModel):
    career_name: str = Field(min_length=1, max_length=255)
    match_percentage: int = Field(ge=0, le=100)
    ai_insight: str = Field(
        min_length=1,
        max_length=200,
        description="8-18 words only; one short personalized sentence.",
    )
    why_this_career: list[str] = Field(
        min_length=1,
        max_length=5,
        description=(
            "Up to 5 short reasons; each reason must be 5-12 words only "
            "(phrase, not a sentence)."
        ),
    )
    required_skills: list[str] = Field(min_length=1, max_length=20)
    required_education: RequiredEducation | None = None
    career_factors: CareerFactors
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
    career_index: int = Field(ge=0, lt=TOP_SUGGESTION_COUNT, exclude=True)
    career_name: str = Field(default="", max_length=255)


EASY_DECISION_TITLES = (
    "Best for quick start",
    "Best for high salary",
    "Best long term bet",
    "Most stable career",
)


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

    @field_validator("easy_decision_making")
    @classmethod
    def require_easy_decision_titles(
        cls, value: list[EasyDecisionItem]
    ) -> list[EasyDecisionItem]:
        titles = {item.title.strip() for item in value}
        missing = [title for title in EASY_DECISION_TITLES if title not in titles]
        if missing:
            raise ValueError(
                "easy_decision_making missing required titles: " + ", ".join(missing)
            )
        return value[:EASY_DECISION_COUNT]

    @model_validator(mode="after")
    def require_easy_decision_careers_from_top_suggestions(
        self,
    ) -> AIRecommendationPayload:
        for card in self.easy_decision_making:
            if card.career_index >= len(self.top_suggestions):
                raise ValueError(
                    "easy_decision_making career_index must reference top_suggestions"
                )
            card.career_name = self.top_suggestions[card.career_index].career_name
        return self
