from __future__ import annotations

from typing import Any

from assessment_career.models import (
    CareerRecommendation,
    CareerSuggestion,
    ChatMessage,
    ChatSession,
)
from recommendation.engine.chat_helpers import (
    as_list,
    compact_text,
    education_label,
    format_education,
    format_other_suggestions,
)
from recommendation.engine.chat_service import BaseAIChatService


def _format_career_factors(value: Any) -> str:
    if not isinstance(value, dict):
        return compact_text(value, 350) if value else "Not specified"
    salary = value.get("salary") or {}
    salary_text = ""
    if isinstance(salary, dict):
        average = str(salary.get("average") or "").strip()
        growth = str(salary.get("growth_rate") or "").strip()
        salary_text = " ".join(part for part in (average, growth) if part)
    job_security = value.get("job_security") or {}
    job_text = ""
    if isinstance(job_security, dict):
        level = str(job_security.get("level") or "").strip()
        demand = str(job_security.get("market_demand_growth") or "").strip()
        job_text = " ".join(part for part in (level, demand) if part)
    learning_curve = value.get("learning_curve") or {}
    learning_text = ""
    if isinstance(learning_curve, dict):
        learning_text = str(learning_curve.get("level") or "").strip()
    parts = [
        f"salary {salary_text}" if salary_text else "",
        (
            f"growth {value.get('growth_potential')}"
            if value.get("growth_potential")
            else ""
        ),
        (
            f"work-life {value.get('work_life_balance')}"
            if value.get("work_life_balance")
            else ""
        ),
        f"job security {job_text}" if job_text else "",
        (
            f"skill match {value.get('skill_match')}%"
            if value.get("skill_match") is not None
            else ""
        ),
        f"learning curve {learning_text}" if learning_text else "",
        f"risk {value.get('risk_level')}" if value.get("risk_level") else "",
    ]
    return "; ".join(part for part in parts if part) or "Not specified"


def _format_roadmap(value: Any) -> str:
    if not isinstance(value, dict):
        return compact_text(value, 350) if value else "Not specified"
    phase_labels = {
        "next_3_months": "0-3 months",
        "next_3_to_6_months": "3-6 months",
        "next_6_to_9_months": "6-9 months",
        "next_9_to_12_months": "9-12 months",
    }
    steps = []
    for key, label in phase_labels.items():
        tasks = value.get(key) or []
        if not isinstance(tasks, list) or not tasks:
            continue
        first_task = tasks[0]
        if isinstance(first_task, dict):
            title = str(first_task.get("task_title") or "").strip()
            description = str(first_task.get("task_description") or "").strip()
            text = title or description
        else:
            text = str(first_task).strip()
        if text:
            steps.append(f"{label}: {compact_text(text, 80)}")
    return "; ".join(steps) or "Not specified"


def _build_student_career_context(suggestion) -> str:
    lines = [
        f"Career: {suggestion.career_name}",
        f"Match: {suggestion.match_percentage}%",
        f"Insight: {suggestion.ai_insight}",
        f"Why this career: {', '.join(as_list(suggestion.why_this_career)[:4])}",
        f"Skills: {', '.join(as_list(suggestion.required_skills)[:8])}",
        f"Education: {format_education(suggestion.required_education)}",
        f"Career factors: {_format_career_factors(suggestion.career_factors)}",
        f"Roadmap: {_format_roadmap(suggestion.career_roadmap)}",
        f"Other suggested careers: {format_other_suggestions(suggestion)}",
    ]
    return "\n".join(line for line in lines if line and not line.endswith(": "))


def _get_student_chips(suggestion) -> list[str]:
    career = (suggestion.career_name or "this career").strip()
    skills = as_list(suggestion.required_skills)
    first_skill = skills[0] if skills else ""
    education = education_label(suggestion.required_education)
    salary = _factor_value(suggestion.career_factors, "salary")
    growth = _factor_value(suggestion.career_factors, "growth_potential")

    questions = []
    if first_skill:
        questions.append(f"How important is {first_skill} for {career}?")
    else:
        questions.append(f"What skills should I build first for {career}?")

    if salary:
        questions.append("What does this salary mean for a beginner in India?")
    else:
        questions.append(f"What salary range can I expect in India for {career}?")

    if education:
        questions.append(f"Is {education} enough to start in {career}?")
    elif growth:
        questions.append(f"How stable is {career} for the next few years?")
    else:
        questions.append(f"What should my 6-month roadmap look like for {career}?")

    return questions[:3]


def _factor_value(value: Any, key: str) -> str:
    if isinstance(value, dict):
        item = value.get(key)
        if isinstance(item, dict):
            return str(item.get("value") or item.get("average") or "").strip()
        return str(item or "").strip()
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("label") or "").casefold()
            if key.replace("_", " ") in name:
                return str(item.get("value") or "").strip()
    return ""


StudentChatService = BaseAIChatService(
    suggestion_model=CareerSuggestion,
    chat_session_model=ChatSession,
    chat_message_model=ChatMessage,
    build_career_context=_build_student_career_context,
    get_chips=_get_student_chips,
    profile_type=CareerRecommendation.ProfileType.STUDENT,
)
