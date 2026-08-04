from __future__ import annotations

import logging

from django.conf import settings
from django.db.models import Q
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
from project_recommendation.models import ProjectRecommendation
from project_recommendation.serializers import ProjectRecommendationSerializer
from project_recommendation.services.project_service import ProjectRecommendationService
from utils.pagination import Pagination
from utils.throttles import (
    ProjectRecommendationRateThrottle,
    ProjectRecommendationReadRateThrottle,
)
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

    def get_throttles(self):
        """Cheap DB reads get a generous limit; the LLM POST keeps 10/min."""
        if self.request.method == "GET":
            return [ProjectRecommendationReadRateThrottle()]
        return [ProjectRecommendationRateThrottle()]

    def get(self, request, *args, **kwargs):
        """
        GET /api/project-recommendations/?assessment_id=19

        Returns the saved project recommendation for the assessment, or a
        paginated list of all saved recommendations for the logged-in user
        when assessment_id is omitted. Data is read from the
        ProjectRecommendation table (persisted by the POST endpoint).
        """
        queryset = ProjectRecommendation.objects.filter(
            user=request.user,
            deleted=False,
        ).order_by("-last_recommended_at", "-id")

        assessment_id = request.query_params.get("assessment_id")
        if assessment_id:
            try:
                assessment_id = int(assessment_id)
            except (TypeError, ValueError):
                return Response(
                    {
                        "success": False,
                        "message": "assessment_id must be an integer",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            record = queryset.filter(
                Q(student_assessment_id=assessment_id)
                | Q(parent_assessment_id=assessment_id)
                | Q(professional_assessment_id=assessment_id)
            ).first()
            if not record:
                return Response(
                    {
                        "success": False,
                        "message": "Project recommendation not found for this assessment",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            serializer = ProjectRecommendationSerializer(record)
            return Response({"success": True, "data": serializer.data})

        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = ProjectRecommendationSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})

        paginator = Pagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = ProjectRecommendationSerializer(page, many=True)
            return paginator.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = ProjectRecommendationSerializer(queryset, many=True)
        return paginator.get_paginated_response(
            {"success": True, "data": serializer.data}
        )

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

        # One generation per assessment, refreshed yearly: if already saved
        # and still within the 365-day cycle (counted from the project
        # recommendation's own date), return the stored result without calling
        # the AI again (no token deduction).
        saved = ProjectRecommendationService.get_existing(
            user=request.user,
            assessment_id=assessment_id,
        )
        if saved is not None:
            return Response(
                {"success": True, "data": saved},
                status=status.HTTP_200_OK,
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
