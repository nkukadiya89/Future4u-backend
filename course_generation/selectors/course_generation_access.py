from __future__ import annotations


def can_user_generate_courses(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.has_perm("course_generation.generate_course")
