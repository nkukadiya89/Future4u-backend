from .models import Courses
from .utils import normalize_list, is_match, normalize_text

def match_courses(ai_skills, ai_education, user,courses_qs):

    ai_skills = normalize_list(ai_skills)
    ai_education = normalize_list(ai_education)

    user_city = user.city if user.is_authenticated else None

    courses = courses_qs
    result = []

    for course in courses:
        course_skills = normalize_list(course.skills)
        course_education = normalize_list(course.education_tags)

        skill_matches = [
            s for s in ai_skills
            if is_match(s, course_skills)
        ]

        if not skill_matches:
            continue 

        score = 0

        score += len(skill_matches) * 10

        for edu in ai_education:
            if is_match(edu, course_education):
                score += 3
                break

        if course.mode == "online":
            score += 8

        elif user_city and course.city:

            if is_match(user_city.name, [course.city.name]):
                score += 10

            elif user_city.state_id == course.city.state_id:
                score += 6

            else:
                score += 2

        result.append({
            "course": course,
            "score": score
        })

    result.sort(key=lambda x: x["score"], reverse=True)

    return [item["course"] for item in result]