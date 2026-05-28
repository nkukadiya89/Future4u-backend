from django.core.exceptions import ObjectDoesNotExist

from .models import Courses
from .utils import normalize_list, is_match, normalize_text, get_next_levels


def _get_user_education_level(user):
    """
    Get the user's current education level code from their profile.

    Checks StudentProfile first, then ProfessionalProfile, then falls
    back to a direct attribute on the User model for backward compatibility.
    """
    try:
        edu_level = user.student_profile.education_level
        if edu_level:
            return edu_level.level_code
    except ObjectDoesNotExist:
        pass

    try:
        edu_level = user.professional_profile.education_level
        if edu_level:
            return edu_level.level_code
    except ObjectDoesNotExist:
        pass

    # Fallback: direct attribute on User (legacy support)
    return getattr(user, "education_level", None)


def match_courses(ai_skills, ai_education, user, courses_qs):

    ai_skills = normalize_list(ai_skills)
    user_level = _get_user_education_level(user)
    has_education = bool(user_level)
    next_levels = get_next_levels(user_level) if user_level else []

    ai_levels = [
        item.get("level_key")
        for item in ai_education.get("levels", [])
        if item.get("level_key")
    ]
    result = []

    for course in courses_qs:

        course_skills = normalize_list(course.skills)
        course_levels = course.education_tags or []

        # --- Education-level gate ---
        if has_education:
            # User's current level matches the course entry requirement
            current_level_match = user_level in course_levels
            # Course is a next-step progression from the user's level
            next_level_match = any(
                level in course_levels for level in next_levels
            )
            # Certifications are always available for upskilling
            if not (
                current_level_match
                or next_level_match
                or course.course_type == "certification"
            ):
                continue
        # else: no education level on profile → show all course types

        skill_matches = [
            s for s in ai_skills if is_match(s, course_skills)
        ]

        if not skill_matches:
            continue

        score = 0
        score += len(skill_matches) * 10

        # Boost for educationally relevant courses
        if has_education and (
            user_level in course_levels
            or any(level in course_levels for level in next_levels)
        ):
            score += 10

        if course.course_type == "certification":
            score += 5

        for level in ai_levels:
            if level in course_levels or (
                level == "professional"
                and course.course_type == "certification"
            ):
                score += 3
                break

        if course.mode == "online":
            score += 5
        elif user.city and course.city:
            if user.city.id == course.city.id:
                score += 10
            elif user.city.state_id == course.city.state_id:
                score += 6

        result.append({"course": course, "score": score})

    result.sort(key=lambda x: x["score"], reverse=True)

    return [item["course"] for item in result]