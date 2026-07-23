from __future__ import annotations

from django.conf import settings

TOP_SUGGESTION_COUNT = 3
EASY_DECISION_COUNT = 4
# Easy Decision cards compare across the top three ranked careers.
EASY_DECISION_CAREER_COUNT = 3


def ai_recommendations_enabled() -> bool:
    """When False, the AI recommendations endpoint is disabled."""
    return bool(getattr(settings, "AI_RECOMMENDATIONS_ENABLED", True))


# ── Study Abroad settings ────────────────────────────────────────────

# Salary disclaimer added to study abroad career recommendations.
STUDY_ABROAD_SALARY_CLAUSE = (
    "abroad varies by country, visa status, degree level, and local demand"
)

# Default exam checks appended when the AI omits them from the response.
STUDY_ABROAD_EXAM_CHECKS = [
    "IELTS/PTE/TOEFL",
    "GRE/GMAT if required for postgraduate/advanced programs",
    "German/French or other language requirements",
]

# Text-normalisation patterns for standardising exam names in AI output.
# Each entry: {"exam_pattern": <regex string>, "normalized": <replacement>}
STUDY_ABROAD_TEXT_REPLACEMENTS = [
    {
        "exam_pattern": r"\b(?:IELTS|PTE|TOEFL)(?:\s*(?:/|,|\band\b|\bor\b)\s*(?:IELTS|PTE|TOEFL))*\b",
        "normalized": "IELTS/PTE/TOEFL",
    },
    {
        "exam_pattern": r"\b(?:GRE|GMAT)(?:\s*(?:/|,|\band\b|\bor\b)\s*(?:GRE|GMAT))*\b",
        "normalized": "GRE/GMAT",
    },
    {
        "exam_pattern": r"\b(?:SAT|ACT)(?:\s*(?:/|,|\band\b|\bor\b)\s*(?:SAT|ACT))*\b",
        "normalized": "course-specific entrance tests",
    },
]
