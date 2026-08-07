"""Shared persistence helpers for project recommendations.

AI mode persists the served response into the ``ProjectRecommendation``
table (upsert per profile_type/domain/domain_category/overview) so
students can see their saved projects again via GET after logging back in.
"""

from __future__ import annotations

from typing import Any

from django.utils import timezone

from project_recommendation.models import ProjectRecommendation


def profile_type_for_user(user) -> str:
    """Map the user's account type to a recommendation profile type."""
    from user.models import User

    mapping = {
        User.Role.STUDENT: ProjectRecommendation.ProfileType.STUDENT,
        User.Role.PARENT: ProjectRecommendation.ProfileType.PARENT,
        User.Role.PROFESSIONAL: ProjectRecommendation.ProfileType.PROFESSIONAL,
    }
    return mapping.get(
        getattr(user, "user_type", None),
        ProjectRecommendation.ProfileType.STUDENT,
    )


def persist_recommendation(
    *,
    user,
    domain: str,
    domain_category: str,
    overview: str = "",
    raw_response: dict[str, Any],
    token_usage: int,
) -> ProjectRecommendation:
    """Upsert one row per (profile_type, domain, domain_category, overview)."""
    relation_kwargs = {"profile_type": profile_type_for_user(user)}
    now = timezone.now()

    match_kwargs = dict(
        relation_kwargs,
        deleted=False,
        domain=domain,
        domain_category=domain_category,
        overview=overview,
    )

    existing = ProjectRecommendation.objects.filter(**match_kwargs).first()
    if existing:
        existing.domain = domain
        existing.domain_category = domain_category
        existing.overview = overview
        existing.raw_ai_response = raw_response
        existing.token_usage = token_usage
        existing.last_recommended_at = now
        existing._request_user = user
        existing.save(
            update_fields=[
                "domain",
                "domain_category",
                "overview",
                "raw_ai_response",
                "token_usage",
                "last_recommended_at",
                "updated_at",
                "updated_by",
            ]
        )
        return existing

    record = ProjectRecommendation(
        user=user,
        **relation_kwargs,
        domain=domain,
        domain_category=domain_category,
        overview=overview,
        raw_ai_response=raw_response,
        token_usage=token_usage,
        last_recommended_at=now,
    )
    record._request_user = user
    record.save()
    return record
