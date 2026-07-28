"""
Dispatch assessment IDs to the correct recommendation / chat service.

Resolves which assessment model (Student, Parent, Professional) an ID belongs to
and returns the appropriate service.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from recommendation.exceptions import AssessmentNotFoundError

logger = logging.getLogger(__name__)


_VALID_PROFILE_TYPES = {"student", "parent", "professional"}


class InvalidProfileTypeError(ValueError):
    """Raised when an invalid profile_type value is provided."""


@dataclass
class DispatchResult:

    service: Any
    profile_type: str


def _models():
    from assessment.models import (
        ParentAssessment,
        ProfessionalAssessment,
        StudentAssessment,
    )

    return {
        "student": StudentAssessment,
        "parent": ParentAssessment,
        "professional": ProfessionalAssessment,
    }


def _recommendation_services():
    from recommendation.profiles.parent.service import ParentRecommendationService
    from recommendation.profiles.professional.service import (
        ProfessionalRecommendationService,
    )
    from recommendation.profiles.student.service import StudentRecommendationService

    return {
        "student": StudentRecommendationService,
        "parent": ParentRecommendationService,
        "professional": ProfessionalRecommendationService,
    }


def _chat_services():
    from recommendation.profiles.parent.chat_service import ParentChatService
    from recommendation.profiles.professional.chat_service import (
        ProfessionalChatService,
    )
    from recommendation.profiles.student.chat_service import StudentChatService

    return {
        "student": StudentChatService,
        "parent": ParentChatService,
        "professional": ProfessionalChatService,
    }


def _validate(profile_type: str) -> str:
    normalised = profile_type.strip().lower()
    if normalised not in _VALID_PROFILE_TYPES:
        raise InvalidProfileTypeError(
            f"Invalid profile_type: '{profile_type}'. "
            f"Must be one of: {', '.join(sorted(_VALID_PROFILE_TYPES))}"
        )
    return normalised


def resolve_recommendation_service(
    assessment_id: int,
    profile_type: str,
) -> DispatchResult:
    """Return a ``DispatchResult`` with the correct recommendation service.

    ``profile_type`` is **required** — the caller must determine the type
    (e.g. by querying the assessment with a user filter) before calling
    this function so ambiguous-ID collisions across user types are avoided.
    """
    profile_type = _validate(profile_type)
    models = _models()
    if (
        not models[profile_type]
        .objects.filter(id=assessment_id, deleted=False)
        .exists()
    ):
        raise AssessmentNotFoundError("Assessment not found")
    svc = _recommendation_services()
    return DispatchResult(service=svc[profile_type](), profile_type=profile_type)


def resolve_chat_service(
    assessment_id: int,
    profile_type: str,
) -> DispatchResult:
    """Return a ``DispatchResult`` with the correct chat service instance.

    ``profile_type`` is **required** — see ``resolve_recommendation_service``
    for the rationale.
    """
    profile_type = _validate(profile_type)
    models = _models()
    if (
        not models[profile_type]
        .objects.filter(id=assessment_id, deleted=False)
        .exists()
    ):
        raise AssessmentNotFoundError("Assessment not found")
    svc = _chat_services()
    return DispatchResult(service=svc[profile_type], profile_type=profile_type)
