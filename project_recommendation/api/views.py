from __future__ import annotations

import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from user.permissions import IsIndividualUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from ai.exceptions import AIConfigurationError as AIProviderConfigError
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
    GET /api/project-recommendations/{suggestion_id}/

    Generates AI-powered personal project ideas based on a selected career
    suggestion from the student's career recommendation.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsIndividualUser]
    throttle_classes = [ProjectRecommendationRateThrottle]

    def get(self, request, suggestion_id, *args, **kwargs):
        # Check token availability bef
        # /
        # ore AI call
        try:
            check_token_available(request.user, "project_gen")
        except Exception as exc:
            logger.warning(
                "Token check failed for user=%s feature=project_gen: %s",
                request.user.id, exc,
            )
            if not settings.DEBUG:
                return Response(
                    {"success": False, "message": str(exc)},
                    status=status.HTTP_402_PAYMENT_REQUIRED,
                )

        token_usage = 0 
        try:
            data, token_usage = _service.generate(
                user=request.user,
                suggestion_id=suggestion_id,
            )
            # Deduct actual LLM token usage after successful AI call
            if not settings.DEBUG:
                try:
                    deduct_monthly_tokens(request.user, token_usage)
                except Exception as exc:
                    logger.error(
                        "TOKEN_RECONCILE user=%s feature=project_gen cost=%s err=%s",
                        request.user.id, token_usage, exc,
                    )
            return Response(
                {"success": True, "data": data},
                status=status.HTTP_200_OK,
            )
        except ProjectRecommendationAccessDeniedError:
            return Response(
                {
                    "success": False,
                    "message": "Career suggestion not found or access denied",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except (ProjectRecommendationConfigurationError, AIProviderConfigError) as exc:
            logger.error("Project recommendation configuration error: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": "AI project recommendation is temporarily unavailable",
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
                    or "Unable to generate project ideas. Please try again.",
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
                    "message": "Unable to generate project ideas",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ProjectRecommendationBatchAPIView(APIView):
    """
    GET /api/project-recommendations/by-recommendation/{recommendation_id}/

    Generates AI-powered personal project ideas for ALL career suggestions
    in a single recommendation. Returns projects grouped by career.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsIndividualUser]
    throttle_classes = [ProjectRecommendationRateThrottle]

    def get(self, request, recommendation_id, *args, **kwargs):
        # Check token availability before AI call
        try:
            check_token_available(request.user, "project_gen")
        except Exception as exc:
            logger.warning(
                "Token check failed for user=%s feature=project_gen: %s",
                request.user.id, exc,
            )
            if not settings.DEBUG:
                return Response(
                    {"success": False, "message": str(exc)},
                    status=status.HTTP_402_PAYMENT_REQUIRED,
                )

        total_token_usage = 0
        try:
            data, total_token_usage = _service.generate_batch(
                user=request.user,
                recommendation_id=recommendation_id,
            )
            # Deduct actual LLM token usage after successful AI call
            if not settings.DEBUG:
                try:
                    deduct_monthly_tokens(request.user, total_token_usage)
                except Exception as exc:
                    logger.error(
                        "TOKEN_RECONCILE user=%s feature=project_gen cost=%s err=%s",
                        request.user.id, total_token_usage, exc,
                    )
            return Response(
                {"success": True, "data": data},
                status=status.HTTP_200_OK,
            )
        except ProjectRecommendationAccessDeniedError:
            return Response(
                {
                    "success": False,
                    "message": "Career recommendation not found or access denied",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except (ProjectRecommendationConfigurationError, AIProviderConfigError) as exc:
            logger.error("Project recommendation configuration error: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": "AI project recommendation is temporarily unavailable",
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
                    or "Unable to generate project ideas. Please try again.",
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
                    "message": "Unable to generate project ideas",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
