from __future__ import annotations


def can_user_generate_internships(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.has_perm("internship_generation.generate_internship")
