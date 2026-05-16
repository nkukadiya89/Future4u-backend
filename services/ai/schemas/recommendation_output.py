from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class TopSuggestionItem(BaseModel):
    career_name: str = Field(min_length=1, max_length=255)
    match_percentage: int = Field(ge=0, le=100)
    ai_insight: str = Field(min_length=1, max_length=2000)
    why_this_career: list[str] = Field(min_length=1, max_length=8)
    required_skills: list[str] = Field(default_factory=list, max_length=20)
    required_education: dict[str, Any] = Field(default_factory=dict)
    career_factors: dict[str, Any] = Field(default_factory=dict)
    career_roadmap: dict[str, Any] = Field(default_factory=dict)

    @field_validator("why_this_career")
    @classmethod
    def strip_reasons(cls, value: list[str]) -> list[str]:
        cleaned = [str(v).strip() for v in value if str(v).strip()]
        if not cleaned:
            raise ValueError("why_this_career must contain at least one item")
        return cleaned[:8]


class EasyDecisionItem(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    career_name: str = Field(min_length=1, max_length=255)
    reason: str = Field(min_length=1, max_length=1000)


class AIRecommendationPayload(BaseModel):
    top_suggestions: list[TopSuggestionItem] = Field(min_length=1, max_length=5)
    easy_decision_making: list[EasyDecisionItem] = Field(min_length=1, max_length=5)

    @field_validator("top_suggestions")
    @classmethod
    def limit_suggestions(cls, value: list[TopSuggestionItem]) -> list[TopSuggestionItem]:
        return value[:5]

    @field_validator("easy_decision_making")
    @classmethod
    def limit_decisions(cls, value: list[EasyDecisionItem]) -> list[EasyDecisionItem]:
        return value[:5]
