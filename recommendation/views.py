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
from utils.token_check import check_and_deduct_token, deduct_monthly_tokens
from recommendation.generators.ai_recommendation_generator import RecommendationGenerator
from recommendation.engine.chat_service import BaseAIChatService
from subscription.models import FeatureUsage
from assessment_career.models import CareerRecommendation
from django.db.models import Q

logger = logging.getLogger(__name__)


class RecommendationAPIView(APIView):
    """
    Unified recommendation endpoint.

    Auto-detects the assessment type (Student / Parent / Professional) from the
    assessment_id and dispatches to the correct service implementation.

    Each assessment can generate a recommendation exactly once (enforced via
    the OneToOne relationship on CareerRecommendation).
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [RecommendationRateThrottle]

    def get(self, request, assessment_id, *args, **kwargs):
        try:
            usage = FeatureUsage.objects.filter(
                user=request.user, feature_code="assessment"
            ).first()
            if not usage or usage.used <= 0:
                raise Exception(
                    "Please complete a profile assessment first to get career recommendations."
                )
        except Exception as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        try:
            profile_type = request.query_params.get("profile_type")
            result = resolve_recommendation_service(
                assessment_id, profile_type=profile_type
            )

            # ── 1 assessment = 1 recommendation ────────────────────────
            # The OneToOneField on CareerRecommendation enforces this at
            # the DB level; we catch it early to show a clear error.
            reco_exists = CareerRecommendation.objects.filter(
                user=request.user,
            ).filter(
                Q(student_assessment_id=assessment_id)
                | Q(parent_assessment_id=assessment_id)
                | Q(professional_assessment_id=assessment_id)
            ).exists()

            if reco_exists:
                return Response(
                    {
                        "success": False,
                        "message": "A recommendation has already been generated for this assessment. "
                        "You can view it in your career suggestions.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check token availability before AI generation
            try:
                check_and_deduct_token(request.user, "recommendation")
            except Exception as exc:
                return Response(
                    {"success": False, "message": str(exc)},
                    status=status.HTTP_402_PAYMENT_REQUIRED,
                )

            data = result.service.generate(
                assessment_id=assessment_id,
                user=request.user,
            )
            # Deduct actual LLM token usage after successful AI call
            try:
                deduct_monthly_tokens(request.user, RecommendationGenerator._last_token_usage)
            except Exception as exc:
                logger.warning("Monthly token deduction failed: %s", exc)
                return Response(
                    {"success": False, "message": str(exc)},
                    status=status.HTTP_402_PAYMENT_REQUIRED,
                )

            return Response(
                {
                    "success": True,
                    "profile_type": result.profile_type,
                    "data": data,
                },
                status=status.HTTP_200_OK,
            )
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
            return Response(
                {
                    "success": True,
                    "profile_type": result.profile_type,
                    "data": data,
                },
                status=status.HTTP_200_OK,
            )
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
        # Check token availability before AI call
        try:
            check_and_deduct_token(request.user, "ai_chat")
        except Exception as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        try:
            profile_type = request.query_params.get("profile_type")
            result = resolve_chat_service(assessment_id, profile_type=profile_type)
            data = result.service.ask(
                user=request.user,
                assessment_id=assessment_id,
                suggestion_id=request.data.get("suggestion_id"),
                question=request.data.get("message"),
            )
            # Deduct actual LLM token usage after successful AI call
            try:
                deduct_monthly_tokens(request.user, BaseAIChatService._last_token_usage)
            except Exception as exc:
                logger.warning("Monthly token deduction failed: %s", exc)
                return Response(
                    {"success": False, "message": str(exc)},
                    status=status.HTTP_402_PAYMENT_REQUIRED,
                )

            return Response(
                {
                    "success": True,
                    "profile_type": result.profile_type,
                    "data": data,
                },
                status=status.HTTP_200_OK,
            )
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
                {
                    "success": False,
                    "message": "Unable to answer right now. Please try again.",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            logger.exception("Unexpected AI chat error")
            return Response(
                {"success": False, "message": "Unable to answer right now"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
