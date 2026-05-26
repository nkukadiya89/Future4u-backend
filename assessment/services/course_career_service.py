from __future__ import annotations

from assessment.models import CourseCareerMapping, StudentAssessment
from assessment_career.models import CareerRecommendation
from career.models import Career
from courses.models import Course


def resolve_career_ids_from_names(names: list[str]) -> list:
    career_ids: list = []
    seen: set = set()
    for raw in names:
        name = (raw or "").strip()
        if not name:
            continue
        career = (
            Career.objects.filter(
                deleted=False,
                is_active=True,
                career_name__iexact=name,
            )
            .only("id")
            .first()
        )
        if career and career.id not in seen:
            seen.add(career.id)
            career_ids.append(career.id)
    return career_ids


def courses_for_assessment(*, assessment_id: int, user_id: int) -> list[Course]:
    """
    Courses mapped to careers suggested by LLM for this assessment.
    Requires a stored CareerRecommendation with suggestions.
    """
    assessment = StudentAssessment.objects.filter(
        id=assessment_id,
        user_id=user_id,
        deleted=False,
    ).first()
    if not assessment:
        return []

    recommendation = (
        CareerRecommendation.objects.filter(
            assessment=assessment,
            user_id=user_id,
            deleted=False,
        )
        .prefetch_related("suggestions")
        .first()
    )
    if not recommendation:
        return []

    names = [
        s.career_name
        for s in recommendation.suggestions.filter(deleted=False).order_by(
            "display_order"
        )
        if s.career_name
    ]
    career_ids = resolve_career_ids_from_names(names)
    if not career_ids:
        return []

    mappings = (
        CourseCareerMapping.objects.filter(
            career_id__in=career_ids,
            course__deleted=False,
        )
        .select_related("course")
        .order_by("-relevance_score", "course_id")
    )
    courses: list[Course] = []
    seen_course_ids: set[int] = set()
    for row in mappings:
        if row.course_id in seen_course_ids:
            continue
        seen_course_ids.add(row.course_id)
        courses.append(row.course)
    return courses
