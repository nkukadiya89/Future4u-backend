import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_log.services import log_event
from recommendation.engine.dispatch import (
    resolve_chat_service,
    resolve_recommendation_service,
)
from recommendation.exceptions import (
    AIConfigurationError,
    AIGenerationError,
    AmbiguousAssessmentError,
    AssessmentAccessDeniedError,
    AssessmentNotFoundError,
    AssessmentNotReadyError,
)
from utils.throttles import AIChatRateThrottle, RecommendationRateThrottle

logger = logging.getLogger(__name__)


class RecommendationAPIView(APIView):
    """
    Unified recommendation endpoint.

    Auto-detects the assessment type (Student / Parent / Professional) from the
    assessment_id and dispatches to the correct service implementation.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [RecommendationRateThrottle]

    def get(self, request, assessment_id, *args, **kwargs):
        try:
            profile_type = request.query_params.get("profile_type")
            result = resolve_recommendation_service(assessment_id, profile_type=profile_type)
            data = result.service.generate(
                assessment_id=assessment_id,
                user=request.user,
            )
            log_event(
                event="ai.recommendation_generated",
                description=f"AI recommendation generated for user {request.user.email}, assessment #{assessment_id}",
                user=request.user,
                entity_type="recommendation",
                entity_id=assessment_id,
                request=request,
            )
            return Response({
                "success": True,
                "profile_type": result.profile_type,
                "data": data,
            }, status=status.HTTP_200_OK)
        except (TypeError, ValueError) as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AmbiguousAssessmentError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
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
                {"success": False, "message": "AI recommendations are temporarily unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except AIGenerationError as exc:
            logger.exception("AI generation failed")
            return Response(
                {"success": False, "message": "Unable to generate recommendations right now. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            logger.exception("Unexpected AI recommendation error")
            return Response(
                {"success": False, "message": "Unable to generate AI recommendations"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RecommendationChatAPIView(APIView):
    """
    Unified chat endpoint (GET = context, POST = ask).

    Auto-detects the assessment type from the assessment_id and dispatches to
    the correct chat service implementation.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIChatRateThrottle]

    def get(self, request, assessment_id, *args, **kwargs):
        try:
            profile_type = request.query_params.get("profile_type")
            result = resolve_chat_service(assessment_id, profile_type=profile_type)
            data = result.service.context(
                user=request.user,
                assessment_id=assessment_id,
                suggestion_id=request.query_params.get("suggestion_id"),
            )
            return Response({
                "success": True,
                "profile_type": result.profile_type,
                "data": data,
            }, status=status.HTTP_200_OK)
        except (TypeError, ValueError) as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AmbiguousAssessmentError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_409_CONFLICT,
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
            profile_type = request.query_params.get("profile_type")
            result = resolve_chat_service(assessment_id, profile_type=profile_type)
            data = result.service.ask(
                user=request.user,
                assessment_id=assessment_id,
                suggestion_id=request.data.get("suggestion_id"),
                question=request.data.get("message"),
            )
            log_event(
                event="ai.chat_message",
                description=f"AI chat message from user {request.user.email}, assessment #{assessment_id}",
                user=request.user,
                entity_type="recommendation_chat",
                entity_id=assessment_id,
                request=request,
            )
            return Response({
                "success": True,
                "profile_type": result.profile_type,
                "data": data,
            }, status=status.HTTP_200_OK)
        except (TypeError, ValueError) as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AmbiguousAssessmentError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_409_CONFLICT,
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
                {"success": False, "message": "AI chat is temporarily unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except AIGenerationError as exc:
            logger.exception("AI chat failed")
            return Response(
                {"success": False, "message": "Unable to answer right now. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            logger.exception("Unexpected AI chat error")
            return Response(
                {"success": False, "message": "Unable to answer right now"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
