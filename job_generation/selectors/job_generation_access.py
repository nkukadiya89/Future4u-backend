from __future__ import annotations


def can_user_generate_jobs(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.has_perm("job_generation.generate_job")
