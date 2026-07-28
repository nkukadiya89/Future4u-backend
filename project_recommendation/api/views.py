from __future__ import annotations

import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from user.permissions import IsIndividualUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from project_recommendation.exceptions import (
    ProjectRecommendationAccessDeniedError,
    ProjectRecommendationConfigurationError,
    ProjectRecommendationValidationError,
)
from project_recommendation.services.project_service import ProjectRecommendationService
from utils.throttles import ProjectRecommendationRateThrottle
from utils.token_check import check_token_available, deduct_monthly_tokens

logger = logging.getLogger(__name__)

_service = ProjectRecommendationService()


class ProjectRecommendationAPIView(APIView):
    """
    POST /api/project-recommendations/

    Generates 3 AI-powered portfolio project ideas based on the user's
    completed assessment. Resolves domain and domain_category from
    the assessment.

    Request body:
    {
        "assessment_id": 123
    }
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsIndividualUser]
    throttle_classes = [ProjectRecommendationRateThrottle]

    def post(self, request, *args, **kwargs):
        try:
            assessment_id = int(request.data.get("assessment_id", ""))
        except (TypeError, ValueError):
            return Response(
                {
                    "success": False,
                    "message": "assessment_id is required and must be an integer",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            check_token_available(request.user, "project_gen")
        except Exception as exc:
            logger.warning(
                "Token check failed for user=%s feature=project_gen: %s",
                request.user.id,
                exc,
            )
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        if not getattr(settings, "PROJECT_RECOMMENDATION_ENABLED", True):
            return Response(
                {
                    "success": False,
                    "message": "Project recommendations are currently disabled",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        token_usage = 0
        try:
            data, token_usage = _service.generate(
                user=request.user,
                assessment_id=assessment_id,
            )
            try:
                deduct_monthly_tokens(request.user, token_usage)
            except Exception as exc:
                logger.error(
                    "TOKEN_RECONCILE user=%s feature=project_gen cost=%s err=%s",
                    request.user.id,
                    token_usage,
                    exc,
                )
            return Response(
                {"success": True, "data": data},
                status=status.HTTP_200_OK,
            )
        except ProjectRecommendationAccessDeniedError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ProjectRecommendationConfigurationError as exc:
            logger.error("Project recommendation configuration error: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": "AI project recommendations are temporarily unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except ProjectRecommendationValidationError as exc:
            logger.warning(
                "Project recommendation validation failed error=%s details=%s",
                exc.error,
                exc.details,
            )
            return Response(
                {
                    "success": False,
                    "message": str(exc)
                    or "Unable to generate project recommendations. Please try again.",
                    "error": exc.error,
                    "details": exc.details,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except Exception:
            logger.exception("Unexpected project recommendation error")
            return Response(
                {
                    "success": False,
                    "message": "Unable to generate project recommendations",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
