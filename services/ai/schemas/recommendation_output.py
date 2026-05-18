from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.ai.config import TOP_SUGGESTION_COUNT


def _clip(value: object, max_len: int) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


class RoadmapTask(BaseModel):
    task_title: str = Field(min_length=1, max_length=120)
    task_description: str = Field(min_length=1, max_length=1000)


class CareerRoadmap(BaseModel):
    next_3_months: list[RoadmapTask] = Field(min_length=1, max_length=2)
    next_3_to_6_months: list[RoadmapTask] = Field(min_length=1, max_length=2)
    next_6_to_9_months: list[RoadmapTask] = Field(min_length=1, max_length=2)
    next_9_to_12_months: list[RoadmapTask] = Field(min_length=1, max_length=2)


class RequiredEducation(BaseModel):
    primary_degree: str | None = Field(default=None, max_length=255)

    @field_validator("primary_degree", mode="before")
    @classmethod
    def clip_degree(cls, value: object) -> object:
        if value is None:
            return None
        text = str(value).strip()
        return _clip(text, 255) if text else None


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
    model_config = ConfigDict(extra="allow")

    level: str | None = Field(default=None, max_length=100)
    market_demand_growth: str | None = Field(default=None, max_length=100)

    @field_validator("level", "market_demand_growth", mode="before")
    @classmethod
    def clip_security_text(cls, value: object) -> object:
        if value is None:
            return value
        return _clip(value, 100)


class LearningCurveFactor(BaseModel):
    model_config = ConfigDict(extra="allow")

    level: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class CareerFactors(BaseModel):
    salary: SalaryFactor | None = None
    growth_potential: str | None = Field(default=None, max_length=200)
    work_life_balance: str | None = Field(default=None, max_length=200)
    job_security: JobSecurityFactor | None = None
    skill_match: int | None = Field(default=None, ge=0, le=100)
    risk_level: str | None = Field(default=None, max_length=200)
    learning_curve: LearningCurveFactor | None = None

    @field_validator(
        "growth_potential",
        "work_life_balance",
        "risk_level",
        mode="before",
    )
    @classmethod
    def clip_factor_labels(cls, value: object) -> object:
        if value is None:
            return None
        text = str(value).strip()
        return _clip(text, 200) if text else None


class TopSuggestionItem(BaseModel):
    career_name: str = Field(min_length=1, max_length=255)
    match_percentage: int = Field(ge=0, le=100)
    ai_insight: str = Field(min_length=1, max_length=2000)
    why_this_career: list[str] = Field(min_length=1, max_length=5)
    required_skills: list[str] = Field(min_length=1, max_length=20)
    required_education: RequiredEducation | None = None
    career_factors: CareerFactors | None = None
    career_roadmap: CareerRoadmap

    @field_validator("why_this_career")
    @classmethod
    def strip_reasons(cls, value: list[str]) -> list[str]:
        cleaned = [str(v).strip() for v in value if str(v).strip()]
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
    reason: str = Field(min_length=1, max_length=1000)


class AIRecommendationPayload(BaseModel):
    top_suggestions: list[TopSuggestionItem] = Field(
        min_length=1, max_length=TOP_SUGGESTION_COUNT
    )
    easy_decision_making: list[EasyDecisionItem] = Field(
        min_length=1, max_length=TOP_SUGGESTION_COUNT
    )

    @field_validator("top_suggestions")
    @classmethod
    def limit_suggestions(cls, value: list[TopSuggestionItem]) -> list[TopSuggestionItem]:
        return value[:TOP_SUGGESTION_COUNT]

    @field_validator("easy_decision_making")
    @classmethod
    def limit_decisions(cls, value: list[EasyDecisionItem]) -> list[EasyDecisionItem]:
        return value[:TOP_SUGGESTION_COUNT]
