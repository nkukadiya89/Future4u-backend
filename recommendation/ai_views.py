import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from recommendation.exceptions import (
    AIConfigurationError,
    AIGenerationError,
    AssessmentAccessDeniedError,
    AssessmentNotFoundError,
    AssessmentNotReadyError,
)
from recommendation.services.ai_recommendation_service import AIRecommendationService
from utils.throttles import RecommendationRateThrottle

logger = logging.getLogger(__name__)


class AIRecommendationAPIView(APIView):
    """
    GET /api/ai-recommendations/{assessment_id}/
    Generates AI career recommendations from a completed student assessment.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [RecommendationRateThrottle]

    def get(self, request, assessment_id, *args, **kwargs):
        try:
            data = AIRecommendationService().generate(
                assessment_id=assessment_id,
                user=request.user,
            )
            return Response({"success": True, "data": data}, status=status.HTTP_200_OK)
        except AssessmentNotFoundError:
            return Response(
                {"success": False, "message": "Assessment not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except AssessmentAccessDeniedError:
            return Response(
                {"success": False, "message": "Assessment access denied"},
                status=status.HTTP_403_FORBIDDEN,
            )
        except AssessmentNotReadyError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AIConfigurationError as exc:
            logger.error("AI configuration error: %s", exc)
            message = "AI recommendation service is not configured"
            if settings.DEBUG:
                detail = str(exc).strip() or exc.__class__.__name__
                message = f"{message}: {detail}"
            return Response(
                {"success": False, "message": message},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except AIGenerationError as exc:
            logger.exception("AI generation failed")
            message = "Unable to generate recommendations right now. Please try again."
            if settings.DEBUG:
                detail = str(exc).strip() or exc.__class__.__name__
                message = f"{message}: {detail}"
            return Response(
                {"success": False, "message": message},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            logger.exception("Unexpected AI recommendation error")
            message = "Unable to generate AI recommendations"
            if settings.DEBUG:
                detail = str(exc).strip() or exc.__class__.__name__
                message = f"{message}: {detail}"
            return Response(
                {"success": False, "message": message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
