import logging

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
from recommendation.profiles.student.service import AIRecommendationService
from recommendation.profiles.student.chat_service import AIChatService
from utils.throttles import RecommendationRateThrottle, AIChatRateThrottle

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
            return Response(
                {
                    "success": False,
                    "message": "AI recommendations are temporarily unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except AIGenerationError as exc:
            logger.exception("AI generation failed")
            return Response(
                {
                    "success": False,
                    "message": "Unable to generate recommendations right now. Please try again.",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            logger.exception("Unexpected AI recommendation error")
            return Response(
                {"success": False, "message": "Unable to generate AI recommendations"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AIRecommendationChatAPIView(APIView):
    """
    GET /api/ai-recommendations/{assessment_id}/chat/?suggestion_id=1
    Returns selected career context and suggested chips without calling AI.

    POST /api/ai-recommendations/{assessment_id}/chat/
    Career-specific assistant for a saved recommendation suggestion.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIChatRateThrottle]

    def get(self, request, assessment_id, *args, **kwargs):
        try:
            data = AIChatService().context(
                user=request.user,
                assessment_id=assessment_id,
                suggestion_id=request.query_params.get("suggestion_id"),
            )
            return Response({"success": True, "data": data}, status=status.HTTP_200_OK)
        except (TypeError, ValueError) as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AssessmentNotFoundError:
            return Response(
                {"success": False, "message": "Recommendation not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except AssessmentAccessDeniedError:
            return Response(
                {"success": False, "message": "Invalid career suggestion"},
                status=status.HTTP_403_FORBIDDEN,
            )

    def post(self, request, assessment_id, *args, **kwargs):
        try:
            data = AIChatService().ask(
                user=request.user,
                assessment_id=assessment_id,
                suggestion_id=request.data.get("suggestion_id"),
                question=request.data.get("message"),
            )
            return Response({"success": True, "data": data}, status=status.HTTP_200_OK)
        except (TypeError, ValueError) as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AssessmentNotFoundError:
            return Response(
                {"success": False, "message": "Recommendation not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except AssessmentAccessDeniedError:
            return Response(
                {"success": False, "message": "Invalid career suggestion"},
                status=status.HTTP_403_FORBIDDEN,
            )
        except AIConfigurationError as exc:
            logger.error("AI chat configuration error: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": "AI chat is temporarily unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except AIGenerationError as exc:
            logger.exception("AI chat failed")
            return Response(
                {
                    "success": False,
                    "message": "Unable to answer right now. Please try again.",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            logger.exception("Unexpected AI chat error")
            return Response(
                {
                    "success": False,
                    "message": "Unable to answer right now",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
