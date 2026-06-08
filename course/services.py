from django.core.exceptions import ObjectDoesNotExist

from .utils import is_match, get_next_levels


def _get_user_education_level(user):
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

    return getattr(user, "education_level", None)


def match_courses(ai_skills, ai_education, user, courses_qs):

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

        course_levels = course.education_tags or []

        if has_education:
            next_level_match = any(level in course_levels for level in next_levels)
            if not (next_level_match or course.course_type == "certification"):
                continue

        skill_matches = [
            s for s in ai_skills if is_match(s, course.skills)
        ]

        if not skill_matches:
            continue

        score = 0
        score += len(skill_matches) * 10

        if has_education and any(level in course_levels for level in next_levels):
            score += 10

        if course.course_type == "certification":
            score += 5

        for level in ai_levels:
            if level in course_levels or (
                level == "professional" and course.course_type == "certification"
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
    return result[:20]
