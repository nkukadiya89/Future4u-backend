"""
Dispatch assessment IDs to the correct recommendation / chat service.

Resolves which assessment model (Student, Parent, Professional) an ID belongs to
and returns the appropriate service without the caller needing to know the profile type.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from recommendation.exceptions import (
    AmbiguousAssessmentError,
    AssessmentNotFoundError,
)

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
    profile_type: Optional[str] = None,
) -> DispatchResult:
    """Return a ``DispatchResult`` with the correct recommendation service.

    * When ``profile_type`` is provided the lookup is instant — the assessment
      is also verified to exist so the caller gets a 404 early.
    * Otherwise the function collects **all** matching tables and only returns
      a service when exactly one match is found.  If multiple tables contain the
      same ID an ``AmbiguousAssessmentError`` is raised.
    """
    if profile_type:
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

    return _auto_detect(assessment_id, _recommendation_services())


def resolve_chat_service(
    assessment_id: int,
    profile_type: Optional[str] = None,
) -> DispatchResult:
    """Return a ``DispatchResult`` with the correct chat service instance.

    Behaves the same as ``resolve_recommendation_service`` but returns a
    pre-instantiated singleton chat-service instance instead of a class.
    """
    if profile_type:
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

    return _auto_detect(assessment_id, _chat_services())


def _auto_detect(
    assessment_id: int,
    services: dict[str, Any],
) -> DispatchResult:
    models = _models()
    matches: list[str] = []
    for pt in ("student", "parent", "professional"):
        if models[pt].objects.filter(id=assessment_id, deleted=False).exists():
            matches.append(pt)

    if len(matches) == 0:
        raise AssessmentNotFoundError("Assessment not found")

    if len(matches) > 1:
        logger.error(
            "Ambiguous assessment_id %s — found in %s",
            assessment_id,
            ", ".join(matches),
        )
        raise AmbiguousAssessmentError(
            f"Assessment ID {assessment_id} matches multiple profile types. "
            f"Please pass ?profile_type= explicitly."
        )

    detected = matches[0]

    # Log auto-detections so we can track frontend migration progress.
    logger.warning(
        "Auto-detected profile_type=%s for assessment_id=%s (no ?profile_type= sent)",
        detected,
        assessment_id,
    )

    instance = services[detected]()
    return DispatchResult(service=instance, profile_type=detected)
