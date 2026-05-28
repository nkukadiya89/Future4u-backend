from .models import Courses
from .utils import normalize_list, is_match, normalize_text,get_next_levels

def match_courses(ai_skills, ai_education, user,courses_qs):

    ai_skills = normalize_list(ai_skills)
    user_level = getattr(user, "education_level", None)
    next_levels = get_next_levels(user_level)

    ai_levels = [
        item.get("level_key")
        for item in ai_education.get("levels", [])
        if item.get("level_key")
    ]
    result = []

    for course in courses_qs:

        course_skills = normalize_list(course.skills)
        course_levels = course.education_tags or []

        if not any(level in course_levels for level in next_levels) \
           and course.course_type != "certification":
            continue

        skill_matches = [
            s for s in ai_skills if is_match(s, course_skills)
        ]

        if not skill_matches:
            continue

        score = 0
        score += len(skill_matches) * 10

        if any(level in course_levels for level in next_levels):
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

    return [item["course"] for item in result]