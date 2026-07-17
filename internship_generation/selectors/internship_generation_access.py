from __future__ import annotations

from user.models import User


def can_user_generate_internships(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.user_type in (
        User.Role.INSTITUTE,
        User.Role.CORPORATE,
        User.Role.SUPER_ADMIN,
    )
